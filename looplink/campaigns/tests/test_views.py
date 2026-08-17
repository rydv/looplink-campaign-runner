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


@pytest.mark.django_db()
def test_launch_action_transitions_a_ready_draft(client):
    campaign = Campaign.objects.create(
        name="Action campaign",
        starts_at="2026-08-20T10:00Z",
        ends_at="2026-08-22T10:00Z",
    )
    Offer.objects.create(
        campaign=campaign,
        type=Offer.Type.CART_FIXED_DISCOUNT,
        parameters={"amount_off": 5, "min_basket": 25},
    )

    response = client.post(
        reverse("campaigns:action", args=(campaign.pk, "launch")),
        {"version": campaign.version},
    )

    campaign.refresh_from_db()
    assert response.status_code == 302
    assert campaign.status == Campaign.Status.LIVE
    assert campaign.version == 2


@pytest.mark.django_db()
def test_public_campaign_hides_non_live_offers_and_enrolls_once(client):
    campaign = Campaign.objects.create(name="Public campaign")
    Offer.objects.create(
        campaign=campaign,
        type=Offer.Type.CART_FIXED_DISCOUNT,
        parameters={"amount_off": 5, "min_basket": 25},
    )
    url = reverse("campaigns:public", args=(campaign.public_id,))

    response = client.get(url)
    assert response.status_code == 200
    assert "still being prepared" in response.content.decode()
    assert "baskets" not in response.content.decode()

    campaign.status = Campaign.Status.LIVE
    campaign.save(update_fields=("status",))
    response = client.post(url, {"identity": " PERSON@EXAMPLE.COM "})
    assert "You’re in" in response.content.decode()
    assert campaign.enrollments.count() == 1

    response = client.post(url, {"identity": "person@example.com"})
    assert "Welcome back" in response.content.decode()
    assert campaign.enrollments.count() == 1


@pytest.mark.django_db()
def test_public_campaign_invalid_id_returns_an_intentional_response(client):
    response = client.get("/campaigns/c/not-a-public-id/")

    assert response.status_code == 404
    assert "link is not available" in response.content.decode()


@pytest.mark.django_db()
def test_internal_enrollment_count_tracks_first_not_repeat_enrollment(client):
    campaign = Campaign.objects.create(name="Counted campaign", status=Campaign.Status.LIVE)
    url = reverse("campaigns:public", args=(campaign.public_id,))

    assert client.get(reverse("campaigns:index")).context["campaigns"][0].enrollment_count == 0
    client.post(url, {"identity": "person@example.com"})
    assert client.get(reverse("campaigns:index")).context["campaigns"][0].enrollment_count == 1
    client.post(url, {"identity": " PERSON@EXAMPLE.COM "})
    assert client.get(reverse("campaigns:index")).context["campaigns"][0].enrollment_count == 1


@pytest.mark.django_db()
def test_live_campaign_shows_local_distribution_only(client):
    campaign = Campaign.objects.create(name="Shareable", status=Campaign.Status.LIVE)

    response = client.get(reverse("campaigns:edit", args=(campaign.pk,)))

    content = response.content.decode()
    assert response.status_code == 409
    assert f"/campaigns/c/{campaign.public_id}/" in content
    assert "<svg" in content
