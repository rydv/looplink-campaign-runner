from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from looplink.campaigns.models import Campaign, Enrollment, Offer


@pytest.fixture()
def campaign():
    now = timezone.now()
    return Campaign.objects.create(
        name="Weekend rewards",
        starts_at=now,
        ends_at=now + timedelta(days=2),
    )


@pytest.mark.django_db()
def test_campaign_has_an_opaque_unique_public_identifier(campaign):
    assert campaign.public_id
    assert campaign.status == Campaign.Status.DRAFT
    assert campaign.version == 1


@pytest.mark.django_db()
@pytest.mark.parametrize(
    ("offer_type", "parameters"),
    [
        (Offer.Type.PRODUCT_PERCENT_DISCOUNT, {"percent": 10, "applies_to": "SKU-123"}),
        (Offer.Type.CART_FIXED_DISCOUNT, {"amount_off": 5, "min_basket": 30}),
        (Offer.Type.STICKER_EARN, {"stickers": 2, "per_amount": 10}),
    ],
)
def test_each_offer_type_accepts_its_required_parameters(campaign, offer_type, parameters):
    offer = Offer(campaign=campaign, type=offer_type, parameters=parameters)

    offer.full_clean()


@pytest.mark.django_db()
def test_offer_validation_rejects_incomplete_parameters(campaign):
    offer = Offer(
        campaign=campaign,
        type=Offer.Type.PRODUCT_PERCENT_DISCOUNT,
        parameters={"percent": 10},
    )

    with pytest.raises(ValidationError, match="applies_to is required"):
        offer.full_clean()


@pytest.mark.django_db()
def test_multiple_offers_of_the_same_type_are_allowed_and_ordered(campaign):
    later = Offer.objects.create(
        campaign=campaign,
        type=Offer.Type.STICKER_EARN,
        parameters={"stickers": 1, "per_amount": 5},
        position=2,
    )
    earlier = Offer.objects.create(
        campaign=campaign,
        type=Offer.Type.STICKER_EARN,
        parameters={"stickers": 2, "per_amount": 10},
        position=1,
    )

    assert list(campaign.offers.all()) == [earlier, later]


@pytest.mark.django_db()
def test_enrollment_identity_is_unique_within_a_campaign(campaign):
    Enrollment.objects.create(
        campaign=campaign,
        submitted_identity="shopper@example.com",
        normalized_identity="shopper@example.com",
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Enrollment.objects.create(
                campaign=campaign,
                submitted_identity="Shopper@example.com",
                normalized_identity="shopper@example.com",
            )
