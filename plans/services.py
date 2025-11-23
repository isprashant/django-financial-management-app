from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from wallets.models import Wallet, WalletTransaction
from .models import SignupPlan, UserSubscription

User = settings.AUTH_USER_MODEL


class PlanPurchaseError(Exception):
    """Raised when a signup plan cannot be activated."""


def _get_personal_wallet(user) -> Wallet:
    wallet, _ = Wallet.objects.get_or_create(
        user=user,
        wallet_type="PERSONAL",
        defaults={"balance": Decimal("0.00")},
    )
    return wallet


@transaction.atomic
def activate_signup_plan(user, plan_id: int) -> UserSubscription:
    plan = SignupPlan.objects.select_for_update().get(pk=plan_id, is_active=True)

    # Fetch existing subscription, if any
    subscription = (
        UserSubscription.objects.select_for_update()
        .filter(user=user)
        .first()
    )

    if subscription and subscription.plan_id == plan.id:
        raise PlanPurchaseError("You are already on this plan.")

    wallet = _get_personal_wallet(user)
    wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

    if wallet.balance < plan.join_fee:
        raise PlanPurchaseError("Insufficient personal wallet balance. Please add funds.")

    wallet.balance -= plan.join_fee
    wallet.save(update_fields=["balance", "updated_at"])

    txn = WalletTransaction.objects.create(
        wallet=wallet,
        txn_type="TRANSFER",
        amount=plan.join_fee,
        is_credit=False,
        description=f"Signup fee for {plan.name}",
        reference_type="SignupPlan",
        reference_id=str(plan.id),
    )

    now = timezone.now()
    if subscription:
        subscription.plan = plan
        subscription.activated_at = now
        subscription.is_active = True
        subscription.payment_reference = str(txn.id)
        subscription.save(
            update_fields=["plan", "activated_at", "is_active", "payment_reference", "updated_at"]
        )
    else:
        subscription = UserSubscription.objects.create(
            user=user,
            plan=plan,
            activated_at=now,
            is_active=True,
            payment_reference=str(txn.id),
        )

    return subscription
