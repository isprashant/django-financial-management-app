from django.shortcuts import render

# Create your views here.
# apps/tasks/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages

from tasks.models import UserTask
from tasks.forms import TaskRatingForm
from tasks.services import complete_task, TaskCompletionError
from plans.models import UserSubscription


@login_required
def earn_tasks_view(request):
    """
    Show today's pending tasks for the logged-in user on earn.html.
    Completed tasks are not shown.
    """
    user = request.user
    today = timezone.now().date()

    # Get today's tasks that are still PENDING
    pending_tasks = (
        UserTask.objects.select_related("task_type", "movie", "property_listing")
        .filter(user=user, date=today, status="PENDING")
        .order_by("created_at")
    )

    # Optionally: get daily limit & completed count for display
    subscription = getattr(user, "subscription", None)
    max_daily_tasks = None
    completed_count = (
        UserTask.objects.filter(user=user, date=today, status="COMPLETED").count()
    )

    if subscription and subscription.is_active:
        max_daily_tasks = subscription.plan.max_daily_tasks

    context = {
        "pending_tasks": pending_tasks,
        "today": today,
        "max_daily_tasks": max_daily_tasks,
        "completed_count": completed_count,
    }
    return render(request, "ui_gsm/earn.html", context)

@login_required
def task_detail_view(request, pk):
    """
    Detailed view for a single task:
    - Shows movie/property details
    - Accepts rating 1–5
    - On POST: completes the task (rewards, wallet, analytics) and redirects to earn page
    """
    user = request.user

    task = get_object_or_404(
        UserTask.objects.select_related("task_type", "movie", "property_listing"),
        pk=pk,
        user=user,
    )

    # If already completed or rejected, just show a message and redirect
    if task.status == "COMPLETED":
        messages.info(request, "This task has already been completed.")
        return redirect("tasks:earn")
    if task.status == "REJECTED":
        messages.error(request, "This task has been rejected and cannot be completed.")
        return redirect("tasks:earn")

    if request.method == "POST":
        form = TaskRatingForm(request.POST)
        if form.is_valid():
            rating = form.cleaned_data["rating"]
            task.rating = rating  # store user rating

            # Save rating first (but not status)
            task.save(update_fields=["rating", "updated_at"])

            # Now run the full completion flow
            try:
                complete_task(task)
            except TaskCompletionError as e:
                messages.error(request, str(e))
                # If completion fails, we DON'T mark as completed, user can retry
                return redirect("tasks:earn")

            messages.success(
                request,
                "Task completed successfully! Your earnings have been added to your investment wallet.",
            )
            return redirect("tasks:earn")
    else:
        form = TaskRatingForm()

    context = {
        "task": task,
        "form": form,
    }
    return render(request, "tasks/task_detail.html", context)
