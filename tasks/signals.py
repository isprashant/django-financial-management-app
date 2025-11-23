from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from plans.models import UserSubscription
from tasks.models import Movie, PropertyListing, TaskType, UserTask


@dataclass(frozen=True)
class _TaskPayload:
    task_type_code: str
    movie: Optional[Movie] = None
    property_listing: Optional[PropertyListing] = None


def _get_active_task_type(code: str) -> Optional[TaskType]:
    """
    Return an active TaskType for the provided code, if one exists.
    """
    return TaskType.objects.filter(code=code, is_active=True).first()


def _active_subscription_user_ids() -> list[int]:
    """
    Fetch ids for users that currently have an active, non-expired subscription
    and plan. Returning ids avoids pulling full user objects while we bulk-create
    tasks.
    """
    now = timezone.now()
    return list(
        UserSubscription.objects.filter(
            is_active=True,
            plan__is_active=True,
        )
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .values_list("user_id", flat=True)
    )


def _create_tasks_for_payload(payload: _TaskPayload) -> None:
    """
    Bulk create UserTask records for every actively subscribed user based on
    the provided payload (movie/property task type).
    """
    task_type = _get_active_task_type(payload.task_type_code)
    if not task_type:
        return

    today = timezone.localdate()
    task_rows: list[UserTask] = []

    for user_id in _active_subscription_user_ids():
        task_rows.append(
            UserTask(
                user_id=user_id,
                task_type=task_type,
                date=today,
                movie=payload.movie,
                property_listing=payload.property_listing,
            )
        )

    if task_rows:
        # Ignore conflicts so we do not break if a task already exists for
        # a user/content combination for today's date.
        UserTask.objects.bulk_create(task_rows, ignore_conflicts=True)


@receiver(post_save, sender=Movie)
def create_movie_tasks(sender, instance: Movie, created: bool, **kwargs):
    if not created:
        return

    _create_tasks_for_payload(
        _TaskPayload(
            task_type_code="RATE_MOVIE",
            movie=instance,
        )
    )


@receiver(post_save, sender=PropertyListing)
def create_property_tasks(sender, instance: PropertyListing, created: bool, **kwargs):
    if not created:
        return

    _create_tasks_for_payload(
        _TaskPayload(
            task_type_code="RATE_PROPERTY",
            property_listing=instance,
        )
    )
