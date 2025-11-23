from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from analytics.models import DailyUserStatement
from wallets.models import Wallet, WalletTransaction
from .models import Referral, ReferralCode

User = settings.AUTH_USER_MODEL

DEFAULT_BONUS = Decimal(getattr(settings, "REFERRAL_BONUS_POINTS", "50"))


def ensure_referral_code(user) -> ReferralCode:
    code_obj, _ = ReferralCode.objects.get_or_create(user=user)
    return code_obj


def _get_personal_wallet(user) -> Wallet:
    wallet, _ = Wallet.objects.get_or_create(
        user=user, wallet_type="PERSONAL", defaults={"balance": Decimal("0.00")}
    )
    return wallet


def _update_daily_statement(user, delta_amount: Decimal) -> None:
    today = timezone.localdate()
    stmt, _ = DailyUserStatement.objects.get_or_create(
        user=user,
        date=today,
        defaults={
            "earnings_from_tasks": Decimal("0.00"),
            "earnings_from_referrals": Decimal("0.00"),
            "earnings_from_investments": Decimal("0.00"),
            "redeemed_points": Decimal("0.00"),
            "withdrawals": Decimal("0.00"),
            "cumulative_earnings": Decimal("0.00"),
        },
    )
    stmt.earnings_from_referrals += delta_amount
    stmt.cumulative_earnings += delta_amount
    stmt.save(
        update_fields=[
            "earnings_from_referrals",
            "cumulative_earnings",
            "updated_at",
        ]
    )


def record_referral_signup(
    referred_user, referral_code: Optional[str]
) -> Optional[Referral]:
    """
    Create referral record if a valid referral code is supplied during signup.
    """
    if not referral_code:
        return None

    try:
        code_obj = ReferralCode.objects.select_related("user").get(code=referral_code)
    except ReferralCode.DoesNotExist:
        return None

    # Prevent self-referral
    if code_obj.user_id == referred_user.id:
        return None

    # Avoid duplicate referral creation for same referred user
    if Referral.objects.filter(referred=referred_user).exists():
        return None

    referral = Referral.objects.create(
        referrer=code_obj.user,
        referred=referred_user,
        referral_code=code_obj,
        code_used=code_obj.code,
        points_awarded=DEFAULT_BONUS,
    )
    return referral


def award_referral_bonus(referral: Referral) -> bool:
    """
    Credit referral bonus to referrer if not already awarded.
    """
    if referral.is_awarded:
        return False

    with transaction.atomic():
        ref = Referral.objects.select_for_update().get(pk=referral.pk)
        if ref.is_awarded:
            return False

        wallet = _get_personal_wallet(ref.referrer)
        wallet.balance += ref.points_awarded
        wallet.save(update_fields=["balance", "updated_at"])

        WalletTransaction.objects.create(
            wallet=wallet,
            txn_type="REFERRAL_BONUS",
            amount=ref.points_awarded,
            is_credit=True,
            description="Referral signup bonus",
            reference_type="Referral",
            reference_id=str(ref.id),
        )

        ref.is_awarded = True
        ref.awarded_at = timezone.now()
        ref.save(update_fields=["is_awarded", "awarded_at", "updated_at"])

        _update_daily_statement(ref.referrer, ref.points_awarded)

        return True


def handle_successful_signup(user, referral_code: Optional[str]) -> Optional[Referral]:
    """
    Ensure new user has a referral code and process referral bonus.
    """
    ensure_referral_code(user)
    referral = record_referral_signup(user, referral_code)
    if referral:
        award_referral_bonus(referral)
    return referral
