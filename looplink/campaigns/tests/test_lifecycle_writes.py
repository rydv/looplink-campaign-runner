from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from looplink.campaigns.models import Campaign, Offer
from looplink.campaigns.services.lifecycle import CampaignAction, TransitionNotAllowedError
from looplink.campaigns.services.lifecycle_writes import (
    CampaignTransitionConflict,
    transition_campaign,
)


@pytest.fixture()
def ready_campaign():
    now = timezone.now()
    campaign = Campaign.objects.create(
        name="Ready campaign",
        starts_at=now,
        ends_at=now + timedelta(days=1),
    )
    Offer.objects.create(
        campaign=campaign,
        type=Offer.Type.CART_FIXED_DISCOUNT,
        parameters={"amount_off": 5, "min_basket": 25},
    )
    return campaign


@pytest.mark.django_db()
def test_schedule_transitions_a_ready_draft_and_increments_version(ready_campaign):
    transitioned = transition_campaign(
        campaign_id=ready_campaign.pk,
        action=CampaignAction.SCHEDULE,
        expected_version=1,
    )

    assert transitioned.status == Campaign.Status.SCHEDULED
    assert transitioned.version == 2


@pytest.mark.django_db()
def test_launch_can_skip_scheduled_and_end_requires_live(ready_campaign):
    launched = transition_campaign(
        campaign_id=ready_campaign.pk,
        action=CampaignAction.LAUNCH,
        expected_version=1,
    )
    ended = transition_campaign(
        campaign_id=launched.pk,
        action=CampaignAction.END,
        expected_version=2,
    )

    assert ended.status == Campaign.Status.ENDED
    assert ended.version == 3


@pytest.mark.django_db()
def test_transition_checks_readiness_and_version_under_lock(ready_campaign):
    with pytest.raises(CampaignTransitionConflict):
        transition_campaign(
            campaign_id=ready_campaign.pk,
            action=CampaignAction.SCHEDULE,
            expected_version=99,
        )

    ready_campaign.offers.all().delete()
    with pytest.raises(ValidationError, match="Add at least one offer"):
        transition_campaign(
            campaign_id=ready_campaign.pk,
            action=CampaignAction.LAUNCH,
            expected_version=1,
        )

    with pytest.raises(TransitionNotAllowedError, match="Cannot end a draft"):
        transition_campaign(
            campaign_id=ready_campaign.pk,
            action=CampaignAction.END,
            expected_version=1,
        )
