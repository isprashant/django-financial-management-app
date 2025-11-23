from django.contrib import admin
from .models import Redemption, RewardItem


@admin.register(RewardItem)
class RewardItemAdmin(admin.ModelAdmin):
    list_display = ("name", "points_cost", "stock", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Redemption)
class RedemptionAdmin(admin.ModelAdmin):
    list_display = ("user", "reward_item", "quantity", "total_points", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("user__username", "reward_item__name")
