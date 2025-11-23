from django.shortcuts import redirect
from django.urls import reverse
from django.http import Http404

from .models import ReferralCode


def referral_link_redirect(request, slug):
    try:
        code_obj = ReferralCode.objects.get(slug=slug)
    except ReferralCode.DoesNotExist:
        raise Http404("Referral link not found")

    signup_url = reverse("signup")
    return redirect(f"{signup_url}?ref={code_obj.code}")
