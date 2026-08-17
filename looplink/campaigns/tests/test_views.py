from django.urls import reverse


def test_campaign_list_renders_the_dashboard_shell(client):
    response = client.get(reverse("campaigns:index"))

    assert response.status_code == 200
    assert "Campaign workspace" in response.content.decode()


def test_root_redirects_to_campaigns(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response.url == reverse("campaigns:index")
