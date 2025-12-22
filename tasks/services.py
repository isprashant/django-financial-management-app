from decimal import Decimal
from datetime import date
from typing import Iterable
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from django.core.exceptions import ValidationError

from django.conf import settings

from tasks.models import Movie, PropertyListing, TaskType, UserTask
from wallets.models import Wallet, WalletTransaction
from plans.models import UserSubscription
from analytics.models import DailyUserStatement

User = settings.AUTH_USER_MODEL


class TaskCompletionError(Exception):
    """Custom exception for any error during task completion."""
    pass


def _get_investment_wallet(user):
    wallet, _ = Wallet.objects.get_or_create(
        user=user,
        wallet_type="INVESTMENT",
        defaults={"balance": Decimal("0.00")},
    )
    return wallet


def _get_task_reward_for_user(user):
    """
    Determine per-task earning:
    - Based on user's active plan (UserSubscription.plan.daily_task_reward_amount)
    """
    try:
        sub = user.subscription
    except UserSubscription.DoesNotExist:
        raise TaskCompletionError("User does not have an active subscription plan.")

    if not sub.is_active:
        raise TaskCompletionError("User's subscription is not active.")

    return sub.plan.daily_task_reward_amount


def _update_daily_statement_for_task(user, date, delta_amount):
    """
    Simple rule:
    - Increase earnings_from_tasks by delta_amount
    - Also increase cumulative_earnings by delta_amount
    (Assumes cumulative_earnings is always updated incrementally)
    """
    stmt, created = DailyUserStatement.objects.get_or_create(
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

    stmt.earnings_from_tasks += delta_amount
    stmt.cumulative_earnings += delta_amount
    stmt.save(
        update_fields=[
            "earnings_from_tasks",
            "cumulative_earnings",
            "updated_at",
        ]
    )


@transaction.atomic
def complete_task(task: UserTask):
    """
    Core service:
    - Validates task
    - Prevents double completion
    - Enforces daily limit based on user's plan
    - Credits investment wallet
    - Updates UserTask.reward_amount & wallet_txn
    - Updates DailyUserStatement

    Raises TaskCompletionError on any business rule violation.
    """
    # Reload with lock to avoid race conditions
    task = UserTask.objects.select_for_update().select_related(
        "user", "task_type"
    ).get(pk=task.pk)

    # 1. Validate status
    if task.status == "COMPLETED":
        raise TaskCompletionError("This task is already completed.")
    if task.status == "REJECTED":
        raise TaskCompletionError("This task has been rejected and cannot be completed.")

    # 2. Domain validation (movie/property logic, unique constraints)
    try:
        task.full_clean()  # calls clean() + field validation
    except ValidationError as e:
        raise TaskCompletionError(str(e))

    user = task.user
    task_date = task.date

    # 3. Enforce daily limit based on user's plan
    reward_per_task = _get_task_reward_for_user(user)

    # Get user's active plan to read max_daily_tasks
    subscription = user.subscription  # already validated in _get_task_reward_for_user
    max_daily_tasks = subscription.plan.max_daily_tasks

    completed_today_count = UserTask.objects.filter(
        user=user, date=task_date, status="COMPLETED"
    ).count()

    # If this task would exceed the daily limit, block
    if completed_today_count >= max_daily_tasks:
        raise TaskCompletionError(
            f"Daily task limit reached ({max_daily_tasks} tasks for {task_date})."
        )

    # 4. Credit investment wallet
    wallet = _get_investment_wallet(user)

    # Lock wallet row
    wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

    wallet.balance += reward_per_task
    wallet.save(update_fields=["balance", "updated_at"])

    wallet_txn = WalletTransaction.objects.create(
        wallet=wallet,
        txn_type="TASK_EARNING",
        amount=reward_per_task,
        is_credit=True,
        description=f"Earning for task {task.id} ({task.task_type.code}) on {task_date}",
        reference_type="UserTask",
        reference_id=str(task.id),
    )

    # 5. Update task
    task.status = "COMPLETED"
    task.reward_amount = reward_per_task
    task.wallet_txn = wallet_txn
    task.save(update_fields=["status", "reward_amount", "wallet_txn", "updated_at"])

    # 6. Update daily statement
    _update_daily_statement_for_task(user, task_date, reward_per_task)

    return task


def rollover_pending_tasks(target_date: date | None = None) -> int:
    """
    Move all pending tasks that belong to days earlier than `target_date` (or
    today by default) so they become available again for the current day.

    The per-day completion limit is still enforced by `complete_task`, so even
    if many tasks roll over, users can only finish as many as their plan allows.
    """
    target_date = target_date or timezone.localdate()
    now = timezone.now()
    stale_tasks = UserTask.objects.filter(status="PENDING", date__lt=target_date)
    updated_count = stale_tasks.update(date=target_date, updated_at=now)
    return updated_count


def create_tasks_for_new_user(user) -> int:
    """
    For a new user, create pending tasks for all current movies and properties.
    Returns the number of tasks created.
    """
    task_types = TaskType.objects.filter(is_active=True)
    movies: Iterable[Movie] = Movie.objects.all()
    properties: Iterable[PropertyListing] = PropertyListing.objects.all()
    today = timezone.localdate()

    created = 0
    task_type_map = {tt.code.upper(): tt for tt in task_types}

    # Create movie tasks
    movie_type = task_type_map.get("RATE_MOVIE")
    if movie_type:
        movie_tasks = [
            UserTask(
                user=user,
                task_type=movie_type,
                date=today,
                status="PENDING",
                movie=movie,
            )
            for movie in movies
        ]
        UserTask.objects.bulk_create(movie_tasks, ignore_conflicts=True)
        created += len(movie_tasks)

    # Create property tasks
    property_type = task_type_map.get("RATE_PROPERTY")
    if property_type:
        property_tasks = [
            UserTask(
                user=user,
                task_type=property_type,
                date=today,
                status="PENDING",
                property_listing=prop,
            )
            for prop in properties
        ]
        UserTask.objects.bulk_create(property_tasks, ignore_conflicts=True)
        created += len(property_tasks)

    return created


def backfill_tasks_for_users_without_tasks() -> int:
    """
    Create tasks for any existing users that currently have no tasks.
    Returns the total number of tasks created across all users.
    """
    UserModel = get_user_model()
    users_without_tasks = UserModel.objects.annotate(task_count=Count("tasks")).filter(task_count=0)
    total_created = 0
    for user in users_without_tasks:
        total_created += create_tasks_for_new_user(user)
    return total_created
