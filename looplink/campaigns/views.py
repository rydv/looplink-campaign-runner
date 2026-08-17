from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from looplink.campaigns.forms import CampaignForm, OfferFormSet
from looplink.campaigns.models import Campaign
from looplink.campaigns.services.campaign_writes import (
    CampaignWriteConflict,
    DraftCampaignData,
    DraftOfferData,
    create_draft,
    save_draft,
)


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

    return render(
        request,
        "campaigns/internal/campaign_form.html",
        {
            "campaign_form": campaign_form,
            "offer_formset": offer_formset,
            "page_title": "Create campaign",
            "submit_label": "Create draft",
        },
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

    return render(
        request,
        "campaigns/internal/campaign_form.html",
        {
            "campaign": campaign,
            "campaign_form": campaign_form,
            "offer_formset": offer_formset,
            "page_title": "Edit campaign",
            "submit_label": "Save draft",
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


def _locked_campaign_response(request, campaign):
    return HttpResponse(
        render(request, "campaigns/internal/campaign_locked.html", {"campaign": campaign}).content,
        status=409,
    )
