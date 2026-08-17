from dataclasses import dataclass

from looplink.campaigns.models import Campaign
from looplink.campaigns.services.lifecycle import allowed_actions, can_edit_campaign
from looplink.campaigns.services.offers import format_offer


@dataclass(frozen=True)
class InternalCampaignPresentation:
    campaign: Campaign
    is_editable: bool
    allowed_actions: tuple[str, ...]


@dataclass(frozen=True)
class PublicCampaignPresentation:
    name: str
    description: str
    status: str
    is_enrollable: bool
    offers: tuple[str, ...]


def present_internal_campaign(campaign):
    return InternalCampaignPresentation(
        campaign=campaign,
        is_editable=can_edit_campaign(campaign.status),
        allowed_actions=tuple(allowed_actions(campaign.status)),
    )


def present_public_campaign(campaign):
    is_enrollable = campaign.status == Campaign.Status.LIVE
    offers = tuple(format_offer(offer) for offer in campaign.offers.all()) if is_enrollable else ()
    return PublicCampaignPresentation(
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        is_enrollable=is_enrollable,
        offers=offers,
    )
