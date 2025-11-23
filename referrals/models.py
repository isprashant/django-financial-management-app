import uuid

from django.conf import settings
from django.db import models
from core.models import TimeStampedModel


User = settings.AUTH_USER_MODEL


def _generate_code():
    return uuid.uuid4().hex[:12].upper()


def _generate_slug():
    return uuid.uuid4().hex[:10]


class ReferralCode(TimeStampedModel):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="referral_code"
    )
    code = models.CharField(max_length=12, unique=True, db_index=True)
    slug = models.SlugField(max_length=50, unique=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = _generate_code()
        if not self.slug:
            self.slug = _generate_slug()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} ({self.code})"


class Referral(TimeStampedModel):
    referrer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="referrals_made"
    )
    referred = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="referral_info",
        null=True,
        blank=True,
    )
    referral_code = models.ForeignKey(
        ReferralCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals",
    )
    code_used = models.CharField(max_length=12, db_index=True)
    points_awarded = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_awarded = models.BooleanField(default=False)
    awarded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.referrer_id} -> {self.referred_id or 'PENDING'}"
