from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from looplink.campaigns.models import Campaign, Offer
from looplink.campaigns.services.lifecycle import (
    CampaignAction,
    TransitionNotAllowedError,
    allowed_actions,
    assert_transition_allowed,
    campaign_readiness_errors,
    can_edit_campaign,
    validate_campaign_readiness,
)


@pytest.fixture()
def campaign():
    now = timezone.now()
    return Campaign.objects.create(
        name="Weekend rewards",
        starts_at=now,
        ends_at=now + timedelta(days=2),
    )


@pytest.mark.django_db()
def test_draft_allows_schedule_and_launch_but_no_end(campaign):
    assert allowed_actions(campaign.status) == (CampaignAction.SCHEDULE, CampaignAction.LAUNCH)
    assert can_edit_campaign(campaign.status)


@pytest.mark.django_db()
def test_live_only_allows_end(campaign):
    campaign.status = Campaign.Status.LIVE

    assert allowed_actions(campaign.status) == (CampaignAction.END,)
    assert not can_edit_campaign(campaign.status)


@pytest.mark.django_db()
def test_illegal_transition_is_rejected(campaign):
    with pytest.raises(TransitionNotAllowedError, match="Cannot end a draft"):
        assert_transition_allowed(campaign, CampaignAction.END)


@pytest.mark.django_db()
def test_readiness_requires_an_offer_and_complete_window(campaign):
    assert campaign_readiness_errors(campaign) == {
        "offers": "Add at least one offer before scheduling or launching."
    }

    with pytest.raises(ValidationError):
        validate_campaign_readiness(campaign)


@pytest.mark.django_db()
def test_readiness_accepts_a_live_window_and_offer(campaign):
    Offer.objects.create(
        campaign=campaign,
        type=Offer.Type.CART_FIXED_DISCOUNT,
        parameters={"amount_off": 5, "min_basket": 30},
    )

    validate_campaign_readiness(campaign)


@pytest.mark.django_db()
def test_readiness_rejects_a_window_that_has_already_ended(campaign):
    campaign.starts_at = timezone.now() - timedelta(days=2)
    campaign.ends_at = timezone.now() - timedelta(minutes=1)

    errors = campaign_readiness_errors(campaign)

    assert errors["ends_at"] == "Campaign window has already ended."
