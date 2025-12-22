from decimal import Decimal
from typing import Iterable

from django.contrib.auth import get_user_model

from wallets.models import Wallet


def ensure_wallets_for_user(user) -> int:
    """
    Ensure both PERSONAL and INVESTMENT wallets exist for the given user.
    Returns the number of wallets created.
    """
    created = 0
    for wallet_type in ("PERSONAL", "INVESTMENT"):
        _, was_created = Wallet.objects.get_or_create(
            user=user,
            wallet_type=wallet_type,
            defaults={"balance": Decimal("0.00")},
        )
        if was_created:
            created += 1
    return created


def backfill_wallets_for_existing_users() -> int:
    """
    Ensure all users have both wallets; create any missing ones.
    Returns the total number of wallets created.
    """
    UserModel = get_user_model()
    total_created = 0
    # Iterate to avoid complex joins; user count is expected to be moderate.
    for user in UserModel.objects.all():
        total_created += ensure_wallets_for_user(user)
    return total_created
