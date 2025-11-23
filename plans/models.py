from django.db import models
from django.conf import settings
from core.models import TimeStampedModel
from referrals.models import Referral

User = settings.AUTH_USER_MODEL

# Create your models here.
class SignupPlan(TimeStampedModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    join_fee = models.DecimalField(max_digits=12, decimal_places=2)  # INR
    daily_task_reward_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Earning per completed daily task for this plan.",
    )
    max_daily_tasks = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    badge = models.ImageField(upload_to="plans/", blank=True, null=True, help_text="Badge image shown on join page.")

    def __str__(self):
        return f"{self.name} ({self.code})"


class UserSubscription(TimeStampedModel):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="subscription"
    )
    plan = models.ForeignKey(SignupPlan, on_delete=models.PROTECT)
    activated_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    payment_reference = models.CharField(
        max_length=255, blank=True, null=True, help_text="Gateway txn id, order id, etc."
    )

    joined_via_referral = models.ForeignKey(
        Referral, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"{self.user} -> {self.plan}"
