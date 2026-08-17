from django.apps import apps


def test_campaigns_app_is_registered():
    assert apps.get_app_config("campaigns").name == "looplink.campaigns"
