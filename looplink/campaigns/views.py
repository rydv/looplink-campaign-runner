from django.shortcuts import render


def campaign_list(request):
    return render(request, "campaigns/internal/campaign_list.html")
