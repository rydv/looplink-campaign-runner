from enum import StrEnum

from django.core.exceptions import ValidationError
from django.utils import timezone

from looplink.campaigns.models import Campaign


class CampaignAction(StrEnum):
    SCHEDULE = "schedule"
    LAUNCH = "launch"
    END = "end"


class TransitionNotAllowedError(ValidationError):
    pass


_ALLOWED_ACTIONS = {
    Campaign.Status.DRAFT: (CampaignAction.SCHEDULE, CampaignAction.LAUNCH),
    Campaign.Status.SCHEDULED: (CampaignAction.LAUNCH,),
    Campaign.Status.LIVE: (CampaignAction.END,),
    Campaign.Status.ENDED: (),
}


def allowed_actions(status):
    return _ALLOWED_ACTIONS[status]


def can_edit_campaign(status):
    return status == Campaign.Status.DRAFT


def assert_transition_allowed(campaign, action):
    if action not in allowed_actions(campaign.status):
        raise TransitionNotAllowedError(f"Cannot {action} a {campaign.status} campaign.")


def campaign_readiness_errors(campaign, now=None):
    now = now or timezone.now()
    errors = {}

    if not campaign.offers.exists():
        errors["offers"] = "Add at least one offer before scheduling or launching."
    if campaign.starts_at is None:
        errors["starts_at"] = "Enter a campaign start time."
    elif timezone.is_naive(campaign.starts_at):
        errors["starts_at"] = "Campaign start time must include a timezone."
    if campaign.ends_at is None:
        errors["ends_at"] = "Enter a campaign end time."
    elif timezone.is_naive(campaign.ends_at):
        errors["ends_at"] = "Campaign end time must include a timezone."

    if campaign.starts_at and campaign.ends_at and campaign.ends_at <= campaign.starts_at:
        errors["ends_at"] = "Campaign end time must be after its start time."
    elif campaign.ends_at and timezone.is_aware(campaign.ends_at) and campaign.ends_at <= now:
        errors["ends_at"] = "Campaign window has already ended."

    return errors


def validate_campaign_readiness(campaign, now=None):
    errors = campaign_readiness_errors(campaign, now=now)
    if errors:
        raise ValidationError(errors)
