from django.urls import path

from .views import referral_link_redirect

app_name = "referrals"

urlpatterns = [
    path("ref/<slug:slug>/", referral_link_redirect, name="referral_redirect"),
]
