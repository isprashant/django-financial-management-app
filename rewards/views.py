from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, render

from users.models import UserPointsSnapshot
from .models import Redemption, RewardItem


def reward_list(request):
    rewards = RewardItem.objects.filter(is_active=True).order_by("-created_at")
    points_balance = None
    if request.user.is_authenticated:
        snapshot, _ = UserPointsSnapshot.objects.get_or_create(
            user=request.user, defaults={"active_points": Decimal("0.00")}
        )
        points_balance = snapshot.active_points
    return render(
        request,
        "ui_gsm/growth.html",
        {
            "title": "Growth Points",
            "heading": "Redeem Rewards",
            "message": "Use your points to redeem exclusive rewards.",
            "rewards": rewards,
            "points_balance": points_balance,
        },
    )


@login_required
def reward_detail(request, pk):
    reward = get_object_or_404(RewardItem, pk=pk, is_active=True)
    snapshot, _ = UserPointsSnapshot.objects.get_or_create(
        user=request.user, defaults={"active_points": Decimal("0.00")}
    )

    error_message = None
    success_message = None

    if request.method == "POST":
        try:
            quantity = int(request.POST.get("quantity", "1"))
        except ValueError:
            quantity = 1
        quantity = max(1, quantity)
        shipping_address = request.POST.get("shipping_address", "").strip()

        cost = reward.points_cost * Decimal(quantity)

        if not shipping_address:
            error_message = "Delivery address is required."
        elif reward.stock < quantity:
            error_message = "Not enough stock available."
        elif snapshot.active_points < cost:
            error_message = "Insufficient points to redeem this reward."
        else:
            with transaction.atomic():
                reward_locked = RewardItem.objects.select_for_update().get(pk=reward.pk)
                snapshot_locked = UserPointsSnapshot.objects.select_for_update().get(
                    user=request.user
                )

                # Re-check with locks
                if reward_locked.stock < quantity:
                    error_message = "Not enough stock available."
                elif snapshot_locked.active_points < cost:
                    error_message = "Insufficient points to redeem this reward."
                else:
                    reward_locked.stock -= quantity
                    reward_locked.save(update_fields=["stock", "updated_at"])

                    snapshot_locked.active_points -= cost
                    snapshot_locked.save(update_fields=["active_points", "updated_at"])

                    Redemption.objects.create(
                        user=request.user,
                        reward_item=reward_locked,
                        quantity=quantity,
                        total_points=cost,
                        shipping_address=shipping_address,
                    )

                    success_message = "Redemption requested. We'll process your delivery soon."
                    # Refresh current objects
                    reward = reward_locked
                    snapshot = snapshot_locked

    return render(
        request,
        "rewards/reward_detail.html",
        {
            "reward": reward,
            "points_balance": snapshot.active_points,
            "error_message": error_message,
            "success_message": success_message,
        },
    )
