from django.contrib import admin

from .models import InvestmentReturnLog, InvestmentScheme, UserInvestment


@admin.register(InvestmentReturnLog)
class InvestmentReturnLogAdmin(admin.ModelAdmin):
    list_display = ("user_investment", "date", "return_amount")
    list_filter = ("date",)
    search_fields = ("user_investment__user__username", "user_investment__user__email", "user_investment__scheme__name")


@admin.register(InvestmentScheme)
class InvestmentSchemeAdmin(admin.ModelAdmin):
    list_display = ("name", "company_name", "min_amount", "max_amount", "cycle_days", "daily_return_percent", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "company_name")


admin.site.register(UserInvestment)

