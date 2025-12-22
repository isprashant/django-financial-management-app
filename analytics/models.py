from django.db import models
from core.models import TimeStampedModel
from django.conf import settings

User = settings.AUTH_USER_MODEL

# Create your models here.
class DailyUserStatement(TimeStampedModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="daily_statements"
    )
    date = models.DateField()

    # Earnings
    earnings_from_tasks = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    earnings_from_referrals = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    earnings_from_investments = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Outgoing
    redeemed_points = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    withdrawals = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Snapshot totals (optional)
    cumulative_earnings = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )

    class Meta:
        unique_together = ("user", "date")
        ordering = ("-date",)

    def __str__(self):
        username = getattr(self.user, "username", self.user_id)
        return f"{username} @ {self.date}"
