from django.urls import path

from looplink.campaigns.views import campaign_action, campaign_list, create_campaign, edit_campaign, public_campaign

app_name = "campaigns"

urlpatterns = [
    path("", campaign_list, name="index"),
    path("new/", create_campaign, name="create"),
    path("<int:campaign_id>/", edit_campaign, name="edit"),
    path("<int:campaign_id>/actions/<str:action>/", campaign_action, name="action"),
    path("c/<str:public_id>/", public_campaign, name="public"),
]
