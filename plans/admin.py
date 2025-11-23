from django.contrib import admin
from .models import UserSubscription, SignupPlan


@admin.register(SignupPlan)
class SignupPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "join_fee", "daily_task_reward_amount", "max_daily_tasks", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "activated_at", "is_active")
    list_filter = ("is_active", "plan")
    search_fields = ("user__username", "plan__name")

