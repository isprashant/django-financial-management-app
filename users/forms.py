import re

from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import CustomUser, UserProfile


class CustomUserCreationForm(UserCreationForm):
    mobile_number = forms.CharField(
        max_length=20,
        label="Mobile Number",
        help_text="Indian numbers only: 10 digits, starts with 6-9, optional +91 prefix.",
    )
    referral_code = forms.CharField(
        required=False,
        label="Referral Code (optional)",
        help_text="If you have a referral code, enter it here.",
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ["username", "email", "mobile_number", "referral_code"]

    def clean_mobile_number(self):
        raw_mobile = (self.cleaned_data.get("mobile_number") or "").strip()
        normalized = re.sub(r"[\s-]+", "", raw_mobile)

        if normalized.startswith("+"):
            normalized = normalized[1:]
        if len(normalized) > 10 and normalized.startswith("91"):
            normalized = normalized[2:]

        if len(normalized) != 10 or not normalized.isdigit():
            raise forms.ValidationError("Enter a valid Indian mobile number with 10 digits.")
        if normalized[0] not in {"6", "7", "8", "9"}:
            raise forms.ValidationError("Indian mobile numbers must start with 6, 7, 8, or 9.")

        international_format = f"+91{normalized}"
        if UserProfile.objects.filter(
            mobile_number__in=[international_format, normalized]
        ).exists():
            raise forms.ValidationError("This mobile number is already registered.")

        return international_format

    def save(self, commit=True):
        user = super().save(commit=commit)
        mobile_number = self.cleaned_data.get("mobile_number")

        if commit and mobile_number:
            profile, _created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "full_name": user.get_full_name() or user.username,
                    "mobile_number": mobile_number,
                    "withdrawal_method": "",
                    "withdrawal_details": "",
                },
            )
            if profile.mobile_number != mobile_number:
                profile.mobile_number = mobile_number
                profile.save(update_fields=["mobile_number"])

        return user


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = ["username", "email"]


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "full_name",
            "mobile_number",
            "withdrawal_method",
            "withdrawal_details",
            "kyc_status",
            "kyc_document_type",
            "kyc_document_number",
        ]
