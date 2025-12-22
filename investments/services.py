from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from analytics.models import DailyUserStatement
from wallets.models import Wallet, WalletTransaction
from .models import InvestmentReturnLog, InvestmentScheme, UserInvestment

User = settings.AUTH_USER_MODEL


class InvestmentError(Exception):
    """Raised when an investment cannot be created."""


@dataclass(frozen=True)
class _WalletPair:
    personal: Wallet
    investment: Wallet


def _get_wallet(user, wallet_type: str) -> Wallet:
    wallet, _ = Wallet.objects.get_or_create(
        user=user,
        wallet_type=wallet_type,
        defaults={"balance": Decimal("0.00")},
    )
    return wallet


def _get_wallets(user) -> _WalletPair:
    return _WalletPair(
        personal=_get_wallet(user, "PERSONAL"),
        investment=_get_wallet(user, "INVESTMENT"),
    )


def _update_daily_statement_for_investment(user, date, delta_amount: Decimal) -> None:
    stmt, _ = DailyUserStatement.objects.get_or_create(
        user=user,
        date=date,
        defaults={
            "earnings_from_tasks": Decimal("0.00"),
            "earnings_from_referrals": Decimal("0.00"),
            "earnings_from_investments": Decimal("0.00"),
            "redeemed_points": Decimal("0.00"),
            "withdrawals": Decimal("0.00"),
            "cumulative_earnings": Decimal("0.00"),
        },
    )

    stmt.earnings_from_investments += delta_amount
    stmt.cumulative_earnings += delta_amount
    stmt.save(
        update_fields=[
            "earnings_from_investments",
            "cumulative_earnings",
            "updated_at",
        ]
    )


def _calculate_daily_return(amount: Decimal, daily_percent: Decimal) -> Decimal:
    raw = amount * (daily_percent / Decimal("100"))
    return raw.quantize(Decimal("0.01"), rounding=ROUND_DOWN)


@transaction.atomic
def create_user_investment(user, scheme: InvestmentScheme, amount: Decimal) -> UserInvestment:
    now = timezone.now()
    today = timezone.localdate()

    if not scheme.is_active:
        raise InvestmentError("This investment scheme is not active right now.")

    if amount < scheme.min_amount or amount > scheme.max_amount:
        raise InvestmentError(
            f"Amount must be between {scheme.min_amount} and {scheme.max_amount}."
        )

    # Ensure only one active investment in this scheme's cycle
    active_exists = (
        UserInvestment.objects.select_for_update()
        .filter(
            user=user,
            scheme=scheme,
            status="ACTIVE",
        )
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
        .exists()
    )
    if active_exists:
        raise InvestmentError(
            "You already have an active investment in this scheme's cycle."
        )

    wallets = _get_wallets(user)

    # Lock wallets for balance updates
    personal_wallet = Wallet.objects.select_for_update().get(pk=wallets.personal.pk)
    if personal_wallet.balance < amount:
        raise InvestmentError("Insufficient balance in your personal wallet.")

    investment_wallet = Wallet.objects.select_for_update().get(pk=wallets.investment.pk)

    # Debit personal wallet
    personal_wallet.balance -= amount
    personal_wallet.save(update_fields=["balance", "updated_at"])

    debit_txn = WalletTransaction.objects.create(
        wallet=personal_wallet,
        txn_type="TRANSFER",
        amount=amount,
        is_credit=False,
        description=f"Investment into {scheme.name}",
        reference_type="UserInvestment",
    )

    ends_at = now + timedelta(days=scheme.cycle_days)
    investment = UserInvestment.objects.create(
        user=user,
        scheme=scheme,
        amount_invested=amount,
        started_at=now,
        ends_at=ends_at,
        personal_wallet_debit_txn=debit_txn,
    )

    # Backfill reference id now that investment exists
    debit_txn.reference_id = str(investment.id)
    debit_txn.save(update_fields=["reference_id"])

    # Credit first day's return immediately to investment wallet
    daily_return = _calculate_daily_return(amount, scheme.daily_return_percent)
    if daily_return > 0:
        investment_wallet.balance += daily_return
        investment_wallet.save(update_fields=["balance", "updated_at"])

        return_txn = WalletTransaction.objects.create(
            wallet=investment_wallet,
            txn_type="INVESTMENT_RETURN",
            amount=daily_return,
            is_credit=True,
            description=f"Day 1 return for {scheme.name}",
            reference_type="UserInvestment",
            reference_id=str(investment.id),
        )

        InvestmentReturnLog.objects.create(
            user_investment=investment,
            date=today,
            return_amount=daily_return,
            wallet_txn=return_txn,
        )

        investment.last_return_date = today
        investment.save(update_fields=["last_return_date", "updated_at"])

        _update_daily_statement_for_investment(user, today, daily_return)

    return investment


def _credit_single_return(investment: UserInvestment, credit_date) -> bool:
    daily_return = _calculate_daily_return(
        investment.amount_invested, investment.scheme.daily_return_percent
    )
    if daily_return <= 0:
        return False

    with transaction.atomic():
        inv = (
            UserInvestment.objects.select_for_update()
            .select_related("scheme", "user")
            .get(pk=investment.pk)
        )

        # Guard against duplicates or out-of-window credits
        if inv.status != "ACTIVE":
            return False
        if inv.started_at.date() > credit_date:
            return False
        if inv.ends_at.date() < credit_date:
            return False
        if inv.last_return_date and inv.last_return_date >= credit_date:
            return False

        wallets = _get_wallets(inv.user)
        investment_wallet = Wallet.objects.select_for_update().get(
            pk=wallets.investment.pk
        )

        investment_wallet.balance += daily_return
        investment_wallet.save(update_fields=["balance", "updated_at"])

        return_txn = WalletTransaction.objects.create(
            wallet=investment_wallet,
            txn_type="INVESTMENT_RETURN",
            amount=daily_return,
            is_credit=True,
            description=f"Daily return for {inv.scheme.name} ({credit_date})",
            reference_type="UserInvestment",
            reference_id=str(inv.id),
        )

        InvestmentReturnLog.objects.create(
            user_investment=inv,
            date=credit_date,
            return_amount=daily_return,
            wallet_txn=return_txn,
        )

        inv.last_return_date = credit_date
        inv.save(update_fields=["last_return_date", "updated_at"])

        _update_daily_statement_for_investment(inv.user, credit_date, daily_return)

        return True

    return False


def credit_returns_for_investment(
    investment: UserInvestment, up_to_date=None
) -> int:
    """Credit any pending daily returns for a single investment up to the given date."""
    target_date = up_to_date or timezone.localdate()
    start_date = investment.started_at.date()
    last_return_date = investment.last_return_date
    next_date = (
        (last_return_date or (start_date - timedelta(days=1))) + timedelta(days=1)
    )

    if next_date < start_date:
        next_date = start_date

    end_date = min(target_date, investment.ends_at.date())
    if end_date < next_date:
        # Even if no returns to credit, still finalize if past end date
        if target_date >= investment.ends_at.date():
            _complete_investment_if_due(investment)
        return 0

    credited_days = 0
    while next_date <= end_date:
        if _credit_single_return(investment, next_date):
            credited_days += 1
        next_date += timedelta(days=1)

    # Finalize investment if cycle complete
    if target_date >= investment.ends_at.date():
        _complete_investment_if_due(investment)

    return credited_days


def credit_daily_returns(for_date=None) -> int:
    """
    Credit daily returns for all active investments up to the given date.

    Returns the total number of day-credits applied.
    """
    target_date = for_date or timezone.localdate()
    total_credited = 0

    investments = (
        UserInvestment.objects.select_related("scheme", "user")
        .filter(status="ACTIVE")
    )

    for investment in investments:
        total_credited += credit_returns_for_investment(
            investment, up_to_date=target_date
        )

    return total_credited


def _complete_investment_if_due(investment: UserInvestment) -> bool:
    """
    Mark an investment as completed and refund principal if it has ended.
    Returns True if completion was applied.
    """
    now = timezone.now()
    if investment.ends_at > now:
        return False

    with transaction.atomic():
        inv = (
            UserInvestment.objects.select_for_update()
            .select_related("user")
            .get(pk=investment.pk)
        )
        if inv.status != "ACTIVE":
            return False
        if inv.ends_at > now:
            return False

        wallets = _get_wallets(inv.user)
        personal_wallet = Wallet.objects.select_for_update().get(pk=wallets.personal.pk)

        # Avoid double refund
        already_refunded = WalletTransaction.objects.filter(
            wallet=personal_wallet,
            txn_type="INVESTMENT_PRINCIPAL_REFUND",
            reference_type="UserInvestment",
            reference_id=str(inv.id),
        ).exists()

        if not already_refunded:
            personal_wallet.balance += inv.amount_invested
            personal_wallet.save(update_fields=["balance", "updated_at"])

            WalletTransaction.objects.create(
                wallet=personal_wallet,
                txn_type="INVESTMENT_PRINCIPAL_REFUND",
                amount=inv.amount_invested,
                is_credit=True,
                description=f"Principal refund for {inv.scheme.name}",
                reference_type="UserInvestment",
                reference_id=str(inv.id),
            )

        inv.status = "COMPLETED"
        inv.save(update_fields=["status", "updated_at"])
        return True

    return False
