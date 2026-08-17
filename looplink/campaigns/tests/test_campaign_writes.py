import pytest

from looplink.campaigns.models import Campaign
from looplink.campaigns.services.campaign_writes import CampaignWriteConflict, DraftCampaignData, save_draft


@pytest.mark.django_db()
def test_stale_draft_write_does_not_overwrite_current_campaign():
    campaign = Campaign.objects.create(name="Current campaign", version=2)

    with pytest.raises(CampaignWriteConflict, match="has changed"):
        save_draft(
            campaign_id=campaign.pk,
            expected_version=1,
            campaign_data=DraftCampaignData(
                name="Stale title", description="", starts_at=None, ends_at=None
            ),
            offers=[],
        )

    campaign.refresh_from_db()
    assert campaign.name == "Current campaign"
    assert campaign.version == 2
