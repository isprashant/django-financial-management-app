from django.db import models
from core.models import TimeStampedModel
from wallets.models import WalletTransaction
from django.conf import settings

User = settings.AUTH_USER_MODEL
# Create your models here.
# rewards/models.py
class RewardItem(TimeStampedModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    points_cost = models.DecimalField(max_digits=14, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    picture = models.ImageField(upload_to="rewards/", blank=True, null=True)

    def __str__(self):
        return self.name


class Redemption(TimeStampedModel):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("SHIPPED", "Shipped"),
        ("REJECTED", "Rejected"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="redemptions")
    reward_item = models.ForeignKey(RewardItem, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    total_points = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    wallet_txn = models.OneToOneField(
        WalletTransaction, on_delete=models.SET_NULL, null=True, blank=True
    )
    shipping_address = models.TextField()
