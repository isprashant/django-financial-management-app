from django.contrib import admin

from .models import Order, PaymentTransaction


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "status", "created_at", "paid_at")
    list_filter = ("status", "currency")
    search_fields = ("id", "user__username", "reference_id")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "gateway", "txnid", "status", "created_at")
    list_filter = ("status", "gateway")
    search_fields = ("txnid", "gateway_txn_id")
