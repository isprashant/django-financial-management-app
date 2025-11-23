from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    referral_code = forms.CharField(
        required=False,
        label="Referral Code (optional)",
        help_text="If you have a referral code, enter it here.",
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ["username", "email", "age", "referral_code"]


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = ["username", "email", "age"]
