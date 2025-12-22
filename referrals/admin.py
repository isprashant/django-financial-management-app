from django.contrib import admin

from .models import Referral, ReferralCode


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ("id", "referrer_username", "referred_username", "code_used", "points_awarded", "is_awarded", "created_at")
    list_filter = ("is_awarded",)
    search_fields = ("referrer__username", "referrer__email", "referred__username", "referred__email", "code_used")
    list_select_related = ("referrer", "referred", "referral_code")

    @admin.display(ordering="referrer__username", description="Referrer")
    def referrer_username(self, obj):
        return getattr(obj.referrer, "username", None)

    @admin.display(ordering="referred__username", description="Referred")
    def referred_username(self, obj):
        return getattr(obj.referred, "username", None) or "PENDING"


@admin.register(ReferralCode)
class ReferralCodeAdmin(admin.ModelAdmin):
    list_display = ("id", "user_username", "code", "slug", "created_at")
    search_fields = ("user__username", "user__email", "code", "slug")
    list_select_related = ("user",)

    @admin.display(ordering="user__username", description="User")
    def user_username(self, obj):
        return getattr(obj.user, "username", None)
