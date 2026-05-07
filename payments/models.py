from django.db import models
from django.conf import settings
from core.models import TimeStampedModel

User = settings.AUTH_USER_MODEL


class Order(TimeStampedModel):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
        ("EXPIRED", "Expired"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payment_orders")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    purpose = models.CharField(max_length=100, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    reference_type = models.CharField(max_length=50, blank=True, null=True)
    reference_id = models.CharField(max_length=50, blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Order {self.id} - {self.user}"


class PaymentTransaction(TimeStampedModel):
    STATUS_CHOICES = [
        ("INITIATED", "Initiated"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="transactions")
    gateway = models.CharField(max_length=30, default="EASEBUZZ")
    txnid = models.CharField(max_length=64, unique=True)
    gateway_txn_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="INITIATED")
    request_payload = models.JSONField(blank=True, null=True)
    response_payload = models.JSONField(blank=True, null=True)
    error_message = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.gateway} {self.txnid}"
