from django.urls import path

from looplink.campaigns.views import campaign_list

app_name = "campaigns"

urlpatterns = [
    path("", campaign_list, name="index"),
]
