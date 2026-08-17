from django.urls import path

from looplink.campaigns.views import campaign_list, create_campaign, edit_campaign

app_name = "campaigns"

urlpatterns = [
    path("", campaign_list, name="index"),
    path("new/", create_campaign, name="create"),
    path("<int:campaign_id>/", edit_campaign, name="edit"),
]
