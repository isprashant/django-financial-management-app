from django.contrib import admin

from .models import DailyUserStatement


@admin.register(DailyUserStatement)
class DailyUserStatementAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "cumulative_earnings")
    list_filter = ("date",)
    search_fields = ("user__username", "user__email")
