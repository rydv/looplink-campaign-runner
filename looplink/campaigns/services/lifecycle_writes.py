from django.core.exceptions import ValidationError
from django.db import transaction

from looplink.campaigns.models import Campaign
from looplink.campaigns.services.lifecycle import (
    CampaignAction,
    TransitionNotAllowedError,
    assert_transition_allowed,
    validate_campaign_readiness,
)


class CampaignTransitionConflict(ValidationError):
    """Raised when the caller acts on an older campaign representation."""


_NEXT_STATUS = {
    CampaignAction.SCHEDULE: Campaign.Status.SCHEDULED,
    CampaignAction.LAUNCH: Campaign.Status.LIVE,
    CampaignAction.END: Campaign.Status.ENDED,
}


def transition_campaign(*, campaign_id, action, expected_version, now=None):
    """Apply one explicit lifecycle action using current, locked campaign state."""
    try:
        action = CampaignAction(action)
    except ValueError as error:
        raise TransitionNotAllowedError("Unknown campaign lifecycle action.") from error

    with transaction.atomic():
        campaign = Campaign.objects.select_for_update().get(pk=campaign_id)
        if campaign.version != expected_version:
            raise CampaignTransitionConflict(
                "This campaign changed before your action could be applied. Reload and try again."
            )

        assert_transition_allowed(campaign, action)
        if action in (CampaignAction.SCHEDULE, CampaignAction.LAUNCH):
            validate_campaign_readiness(campaign, now=now)

        campaign.status = _NEXT_STATUS[action]
        campaign.version += 1
        campaign.save(update_fields=("status", "version", "updated_at"))

    return campaign
