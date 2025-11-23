from django.db import models
from core.models import TimeStampedModel
from django.conf import settings

User = settings.AUTH_USER_MODEL
# Create your models here.
# finance/models.py
class Wallet(TimeStampedModel):
    WALLET_TYPE_CHOICES = [
        ("PERSONAL", "Personal Wallet"),
        ("INVESTMENT", "Investment Wallet"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wallets")
    wallet_type = models.CharField(max_length=20, choices=WALLET_TYPE_CHOICES)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        unique_together = ("user", "wallet_type")

    def __str__(self):
        return f"{self.user} - {self.wallet_type}"


class WalletTransaction(TimeStampedModel):
    TRANSACTION_TYPE_CHOICES = [
        ("DEPOSIT", "Deposit"),
        ("WITHDRAWAL", "Withdrawal"),
        ("TASK_EARNING", "Task Earning"),
        ("REFERRAL_BONUS", "Referral Bonus"),
        ("INVESTMENT_RETURN", "Investment Return"),
        ("INVESTMENT_PRINCIPAL_REFUND", "Investment Principal Refund"),
        ("REDEEM_PURCHASE", "Redeem Purchase"),
        ("ADJUSTMENT", "Manual Adjustment"),
        ("TRANSFER", "Transfer Between Wallets"),
    ]

    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name="transactions"
    )
    txn_type = models.CharField(max_length=40, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    is_credit = models.BooleanField(
        help_text="True if amount is added to wallet, False if deducted."
    )
    description = models.CharField(max_length=255, blank=True, null=True)

    # For linking back to source event (task, investment, referral, etc.)
    reference_type = models.CharField(
        max_length=50, blank=True, null=True, help_text="e.g. 'UserTask', 'UserInvestment'"
    )
    reference_id = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        sign = "+" if self.is_credit else "-"
        return f"{self.wallet} {sign}{self.amount} ({self.txn_type})"


class Deposit(TimeStampedModel):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="deposits")
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    payment_gateway = models.CharField(max_length=50, blank=True, null=True)
    gateway_txn_id = models.CharField(max_length=255, blank=True, null=True)
    wallet_txn = models.OneToOneField(
        WalletTransaction, on_delete=models.SET_NULL, null=True, blank=True
    )


class WithdrawalRequest(TimeStampedModel):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("PAID", "Paid"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="withdrawals")
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    processed_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True, null=True)
    wallet_txn = models.OneToOneField(
        WalletTransaction, on_delete=models.SET_NULL, null=True, blank=True
    )
