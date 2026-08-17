from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from looplink.campaigns.models import Campaign, Enrollment
from looplink.campaigns.services.identity import normalize_identity


class CampaignUnavailableError(ValidationError):
    pass


def enroll_identity(*, campaign_id, identity):
    normalized = normalize_identity(identity)
    with transaction.atomic():
        campaign = Campaign.objects.select_for_update().get(pk=campaign_id)
        if campaign.status != Campaign.Status.LIVE:
            raise CampaignUnavailableError("This campaign is no longer live.")
        try:
            with transaction.atomic():
                enrollment = Enrollment.objects.create(
                    campaign=campaign,
                    submitted_identity=normalized.submitted,
                    normalized_identity=normalized.normalized,
                )
        except IntegrityError:
            enrollment = Enrollment.objects.get(
                campaign=campaign,
                normalized_identity=normalized.normalized,
            )
            return enrollment, True
        return enrollment, False
