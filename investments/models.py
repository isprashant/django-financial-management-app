from django.db import models
from core.models import TimeStampedModel
from django.conf import settings
from wallets.models import WalletTransaction

User = settings.AUTH_USER_MODEL

# Create your models here.
class InvestmentScheme(TimeStampedModel):
    name = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    min_amount = models.DecimalField(max_digits=14, decimal_places=2)
    max_amount = models.DecimalField(max_digits=14, decimal_places=2)
    cycle_days = models.PositiveIntegerField(
        help_text="Investment cycle length in days."
    )
    daily_return_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Daily return % on invested amount (e.g. 1.5 = 1.5% per day).",
    )
    is_active = models.BooleanField(default=True)
    terms_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.company_name})"
    
class UserInvestment(TimeStampedModel):
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="investments")
    scheme = models.ForeignKey(
        InvestmentScheme, on_delete=models.PROTECT, related_name="user_investments"
    )
    amount_invested = models.DecimalField(max_digits=14, decimal_places=2)
    started_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")

    # Track last interest credit to avoid duplicate daily jobs
    last_return_date = models.DateField(null=True, blank=True)

    # Link to wallet transactions that handled money flow
    personal_wallet_debit_txn = models.OneToOneField(
        WalletTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="investment_principal_debit",
    )

    def __str__(self):
        return f"{self.user} - {self.scheme} - {self.amount_invested}"
    

class InvestmentReturnLog(TimeStampedModel):
    user_investment = models.ForeignKey(
        UserInvestment, on_delete=models.CASCADE, related_name="return_logs"
    )
    date = models.DateField()
    return_amount = models.DecimalField(max_digits=14, decimal_places=2)
    wallet_txn = models.OneToOneField(
        WalletTransaction, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        unique_together = ("user_investment", "date")

    def __str__(self):
        username = getattr(self.user_investment.user, "username", None) if self.user_investment else None
        inv_name = str(self.user_investment) if self.user_investment else "Unknown investment"
        return f"{username or 'User'} - {inv_name} @ {self.date}"

'''
Your cron/job logic:

For each UserInvestment ACTIVE, for each day in cycle not yet credited → create InvestmentReturnLog and credit 
to INVESTMENT wallet via WalletTransaction(txn_type="INVESTMENT_RETURN", is_credit=True, ...).

On cycle end: mark investment COMPLETED and refund principal to PERSONAL wallet via 
WalletTransaction(txn_type="INVESTMENT_PRINCIPAL_REFUND", is_credit=True, ...).
'''
