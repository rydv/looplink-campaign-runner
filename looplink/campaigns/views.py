import uuid

from django.core.exceptions import ValidationError
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from looplink.campaigns.forms import CampaignForm, EnrollmentForm, OfferFormSet
from looplink.campaigns.models import Campaign
from looplink.campaigns.presenters import present_public_campaign
from looplink.campaigns.services.campaign_writes import (
    CampaignWriteConflict,
    DraftCampaignData,
    DraftOfferData,
    create_draft,
    save_draft,
)
from looplink.campaigns.services.enrollments import CampaignUnavailableError, enroll_identity
from looplink.campaigns.services.lifecycle import allowed_actions, campaign_readiness_errors
from looplink.campaigns.services.lifecycle_writes import transition_campaign


def campaign_list(request):
    return render(
        request,
        "campaigns/internal/campaign_list.html",
        {"campaigns": Campaign.objects.prefetch_related("offers").all()},
    )


def create_campaign(request):
    if request.method == "POST":
        campaign_form = CampaignForm(request.POST)
        offer_formset = OfferFormSet(request.POST, prefix="offers")
        if campaign_form.is_valid() and offer_formset.is_valid():
            campaign = create_draft(
                campaign_data=_campaign_data(campaign_form),
                offers=_offer_data(offer_formset),
            )
            return redirect("campaigns:edit", campaign_id=campaign.pk)
    else:
        campaign_form = CampaignForm(initial={"version": 1})
        offer_formset = OfferFormSet(prefix="offers")

    return _render_draft_workspace(
        request,
        campaign_form,
        offer_formset,
        page_title="Create campaign",
        submit_label="Create draft",
    )


def edit_campaign(request, campaign_id):
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    if campaign.status != Campaign.Status.DRAFT:
        return _locked_campaign_response(request, campaign)

    if request.method == "POST":
        campaign_form = CampaignForm(request.POST, instance=campaign)
        offer_formset = OfferFormSet(request.POST, instance=campaign, prefix="offers")
        if campaign_form.is_valid() and offer_formset.is_valid():
            try:
                campaign = save_draft(
                    campaign_id=campaign.pk,
                    expected_version=campaign_form.cleaned_data["version"],
                    campaign_data=_campaign_data(campaign_form),
                    offers=_offer_data(offer_formset),
                )
            except CampaignWriteConflict as error:
                campaign_form.add_error(None, error)
            else:
                return redirect(f"{reverse('campaigns:edit', args=(campaign.pk,))}?saved=1")
    else:
        campaign_form = CampaignForm(instance=campaign)
        offer_formset = OfferFormSet(instance=campaign, prefix="offers")

    return _render_draft_workspace(request, campaign_form, offer_formset, campaign=campaign)


def campaign_action(request, campaign_id, action):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    campaign = get_object_or_404(Campaign, pk=campaign_id)
    try:
        expected_version = int(request.POST["version"])
    except (KeyError, ValueError):
        return _transition_error_response(request, campaign, "The campaign action was missing its version.")

    try:
        campaign = transition_campaign(
            campaign_id=campaign.pk,
            action=action,
            expected_version=expected_version,
        )
    except ValidationError as error:
        campaign.refresh_from_db()
        return _transition_error_response(request, campaign, _validation_message(error))

    return redirect(f"{reverse('campaigns:edit', args=(campaign.pk,))}?transitioned={action}")


def public_campaign(request, public_id):
    try:
        public_id = uuid.UUID(str(public_id))
    except ValueError:
        return render(request, "campaigns/public/invalid.html", status=404)

    campaign = Campaign.objects.prefetch_related("offers").filter(public_id=public_id).first()
    if campaign is None:
        return render(request, "campaigns/public/invalid.html", status=404)

    if campaign.status != Campaign.Status.LIVE:
        return render(request, "campaigns/public/state.html", {"campaign": campaign})

    enrollment_form = EnrollmentForm(request.POST or None)
    enrolled = recognized = False
    if request.method == "POST" and enrollment_form.is_valid():
        try:
            _, recognized = enroll_identity(
                campaign_id=campaign.pk,
                identity=enrollment_form.cleaned_data["identity"],
            )
        except CampaignUnavailableError:
            campaign.refresh_from_db()
            return render(request, "campaigns/public/state.html", {"campaign": campaign})
        except ValidationError as error:
            enrollment_form.add_error("identity", _validation_message(error))
        else:
            enrolled = True

    return render(
        request,
        "campaigns/public/campaign.html",
        {
            "campaign": present_public_campaign(campaign),
            "enrollment_form": enrollment_form,
            "enrolled": enrolled,
            "recognized": recognized,
        },
    )


def _campaign_data(campaign_form):
    return DraftCampaignData(
        name=campaign_form.cleaned_data["name"],
        description=campaign_form.cleaned_data["description"],
        starts_at=campaign_form.cleaned_data["starts_at"],
        ends_at=campaign_form.cleaned_data["ends_at"],
    )


def _offer_data(offer_formset):
    return [
        DraftOfferData(type=form.cleaned_data["type"], parameters=form.cleaned_data["parameters"])
        for form in offer_formset.forms
        if form.cleaned_data and not form.cleaned_data.get("DELETE") and form.cleaned_data.get("type")
    ]


def _render_draft_workspace(
    request,
    campaign_form,
    offer_formset,
    *,
    campaign=None,
    page_title="Edit campaign",
    submit_label="Save draft",
    action_error=None,
):
    return render(
        request,
        "campaigns/internal/campaign_form.html",
        {
            "campaign": campaign,
            "campaign_form": campaign_form,
            "offer_formset": offer_formset,
            "page_title": page_title,
            "submit_label": submit_label,
            "allowed_actions": allowed_actions(Campaign.Status.DRAFT) if campaign else (),
            "readiness_errors": campaign_readiness_errors(campaign) if campaign else {},
            "action_error": action_error,
        },
    )


def _locked_campaign_response(request, campaign, action_error=None):
    return render(
        request,
        "campaigns/internal/campaign_locked.html",
        {
            "campaign": campaign,
            "allowed_actions": allowed_actions(campaign.status),
            "action_error": action_error,
        },
        status=409,
    )


def _transition_error_response(request, campaign, error):
    if campaign.status == Campaign.Status.DRAFT:
        return _render_draft_workspace(
            request,
            CampaignForm(instance=campaign),
            OfferFormSet(instance=campaign, prefix="offers"),
            campaign=campaign,
            action_error=error,
        )
    return _locked_campaign_response(request, campaign, action_error=error)


def _validation_message(error):
    if hasattr(error, "message_dict"):
        return " ".join(message for messages in error.message_dict.values() for message in messages)
    return " ".join(error.messages)
