from datetime import timedelta

import pytest
from django.utils import timezone

from looplink.campaigns.models import Campaign, Offer
from looplink.campaigns.presenters import present_internal_campaign, present_public_campaign
from looplink.campaigns.services.lifecycle import CampaignAction


@pytest.fixture()
def campaign():
    now = timezone.now()
    campaign = Campaign.objects.create(
        name="Weekend rewards",
        description="Rewards for weekend shoppers.",
        starts_at=now,
        ends_at=now + timedelta(days=2),
    )
    Offer.objects.create(
        campaign=campaign,
        type=Offer.Type.PRODUCT_PERCENT_DISCOUNT,
        parameters={"percent": 10, "applies_to": "SKU-123"},
    )
    return campaign


@pytest.mark.django_db()
def test_internal_presentation_exposes_draft_actions(campaign):
    presentation = present_internal_campaign(campaign)

    assert presentation.is_editable
    assert presentation.allowed_actions == (CampaignAction.SCHEDULE, CampaignAction.LAUNCH)


@pytest.mark.django_db()
def test_public_presentation_hides_offers_until_the_campaign_is_live(campaign):
    presentation = present_public_campaign(campaign)

    assert not presentation.is_enrollable
    assert presentation.offers == ()


@pytest.mark.django_db()
def test_public_presentation_formats_live_offer_values(campaign):
    campaign.status = Campaign.Status.LIVE
    campaign.save(update_fields=("status",))

    presentation = present_public_campaign(campaign)

    assert presentation.is_enrollable
    assert presentation.offers == ("10% off SKU-123",)
