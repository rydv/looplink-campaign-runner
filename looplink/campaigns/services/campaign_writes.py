from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from looplink.campaigns.models import Campaign, Offer
from looplink.campaigns.services.lifecycle import can_edit_campaign


class CampaignWriteConflict(ValidationError):
    pass


@dataclass(frozen=True)
class DraftCampaignData:
    name: str
    description: str
    starts_at: object
    ends_at: object


@dataclass(frozen=True)
class DraftOfferData:
    type: str
    parameters: dict


def create_draft(*, campaign_data, offers):
    with transaction.atomic():
        campaign = Campaign.objects.create(
            name=campaign_data.name,
            description=campaign_data.description,
            starts_at=campaign_data.starts_at,
            ends_at=campaign_data.ends_at,
        )
        _replace_offers(campaign, offers)
    return campaign


def save_draft(*, campaign_id, expected_version, campaign_data, offers):
    with transaction.atomic():
        campaign = Campaign.objects.select_for_update().get(pk=campaign_id)
        if not can_edit_campaign(campaign.status):
            raise CampaignWriteConflict("This campaign is locked and can no longer be edited.")
        if campaign.version != expected_version:
            raise CampaignWriteConflict("This campaign has changed. Reload it before saving.")

        campaign.name = campaign_data.name
        campaign.description = campaign_data.description
        campaign.starts_at = campaign_data.starts_at
        campaign.ends_at = campaign_data.ends_at
        campaign.version += 1
        campaign.save()
        _replace_offers(campaign, offers)
    return campaign


def _replace_offers(campaign, offers):
    campaign.offers.all().delete()
    for position, offer_data in enumerate(offers):
        Offer.objects.create(
            campaign=campaign,
            type=offer_data.type,
            parameters=offer_data.parameters,
            position=position,
        )
