from django.db import models
from django.conf import settings
from core.models import TimeStampedModel
import uuid
from django.contrib.auth.models import AbstractUser

# Create your models here.

class CustomUser(AbstractUser):

    age = models.PositiveIntegerField(null=True, blank=True)

User = settings.AUTH_USER_MODEL

class UserProfile(TimeStampedModel):
    KYC_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("VERIFIED", "Verified"),
        ("REJECTED", "Rejected"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    mobile_number = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=255)

    # Withdrawal info (can be UPI, bank, etc.)
    withdrawal_method = models.CharField(
        max_length=50,
        help_text="e.g. UPI, Bank Transfer, Paytm, etc.",
    )
    withdrawal_details = models.TextField(
        help_text="JSON or formatted details for the chosen withdrawal method.",
    )

    # Optional withdrawal password / PIN (store hashed)
    withdrawal_pin_hash = models.CharField(max_length=255, blank=True, null=True)

    # KYC
    kyc_status = models.CharField(
        max_length=20,
        choices=KYC_STATUS_CHOICES,
        default="PENDING",
    )
    kyc_document_type = models.CharField(max_length=50, blank=True, null=True)
    kyc_document_number = models.CharField(max_length=100, blank=True, null=True)
    kyc_document_file = models.FileField(upload_to="kyc/", blank=True, null=True)

    # Referral
    referral_code = models.CharField(max_length=12, unique=True, db_index=True)
    referral_link_slug = models.SlugField(
        max_length=50, unique=True, help_text="Used to build referral URLs."
    )

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = uuid.uuid4().hex[:12].upper()
        if not self.referral_link_slug:
            self.referral_link_slug = uuid.uuid4().hex[:10]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - Profile"

class UserPointsSnapshot(TimeStampedModel):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="user_points_snapshot"
    )
    active_points = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)