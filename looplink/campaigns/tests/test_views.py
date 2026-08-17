import pytest
from django.urls import reverse

from looplink.campaigns.models import Campaign, Offer


@pytest.mark.django_db()
def test_campaign_list_renders_the_dashboard_shell(client):
    response = client.get(reverse("campaigns:index"))

    assert response.status_code == 200
    assert "Campaign workspace" in response.content.decode()


def test_root_redirects_to_campaigns(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response.url == reverse("campaigns:index")


@pytest.mark.django_db()
def test_create_campaign_persists_a_draft_and_offer(client):
    response = client.post(
        reverse("campaigns:create"),
        data={
            "name": "Weekend rewards", "description": "A test campaign",
            "starts_at": "2026-08-20T10:00", "ends_at": "2026-08-22T10:00", "version": "1",
            "offers-TOTAL_FORMS": "1", "offers-INITIAL_FORMS": "0",
            "offers-MIN_NUM_FORMS": "0", "offers-MAX_NUM_FORMS": "1000",
            "offers-0-type": Offer.Type.PRODUCT_PERCENT_DISCOUNT,
            "offers-0-percent": "10", "offers-0-applies_to": "SKU-123",
        },
    )

    assert response.status_code == 302
    campaign = Campaign.objects.get()
    assert response.url == reverse("campaigns:edit", args=(campaign.pk,))
    assert campaign.status == Campaign.Status.DRAFT
    assert campaign.offers.get().parameters == {"percent": 10.0, "applies_to": "SKU-123"}


@pytest.mark.django_db()
def test_invalid_offer_parameters_are_returned_without_creating_a_campaign(client):
    response = client.post(
        reverse("campaigns:create"),
        data={
            "name": "Weekend rewards", "starts_at": "2026-08-20T10:00",
            "ends_at": "2026-08-22T10:00", "version": "1",
            "offers-TOTAL_FORMS": "1", "offers-INITIAL_FORMS": "0",
            "offers-MIN_NUM_FORMS": "0", "offers-MAX_NUM_FORMS": "1000",
            "offers-0-type": Offer.Type.PRODUCT_PERCENT_DISCOUNT, "offers-0-percent": "10",
        },
    )

    assert response.status_code == 200
    assert Campaign.objects.count() == 0
    assert "applies_to is required" in response.content.decode()


@pytest.mark.django_db()
def test_non_draft_campaign_cannot_be_edited_by_a_direct_request(client):
    campaign = Campaign.objects.create(name="Launched campaign", status=Campaign.Status.LIVE)

    response = client.get(reverse("campaigns:edit", args=(campaign.pk,)))

    assert response.status_code == 409
    assert "can no longer be edited" in response.content.decode()
