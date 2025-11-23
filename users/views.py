from django.shortcuts import render
from django.views.generic.edit import CreateView
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy

from analytics.models import DailyUserStatement
from referrals.services import handle_successful_signup
from .forms import CustomUserChangeForm, CustomUserCreationForm


@login_required
def profile_view(request):
    profile = getattr(request.user, "profile", None)
    referral_code = getattr(request.user, "referral_code", None)
    referral_link = None
    if referral_code:
        referral_link = request.build_absolute_uri(
            f"/ref/{referral_code.slug}/"
        )
    statements = DailyUserStatement.objects.filter(user=request.user).order_by("-date")
    return render(
        request,
        "users/profile.html",
        {
            "title": "My Profile",
            "profile": profile,
            "referral_code": referral_code,
            "referral_link": referral_link,
            "statements": statements,
        },
    )


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("login")
    template_name = "signup.html"

    def get_initial(self):
        initial = super().get_initial()
        ref_code = self.request.GET.get("ref")
        if ref_code:
            initial["referral_code"] = ref_code
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        ref_code = form.cleaned_data.get("referral_code")
        handle_successful_signup(self.object, ref_code)
        return response
