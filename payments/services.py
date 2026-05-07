import hashlib
import uuid

from django.conf import settings
from django.utils import timezone

from .models import Order, PaymentTransaction


class EasebuzzConfigError(Exception):
    """Raised when Easebuzz settings are missing."""


def _require_easebuzz_settings():
    if not settings.EASEBUZZ_MERCHANT_KEY or not settings.EASEBUZZ_SALT:
        raise EasebuzzConfigError("Easebuzz merchant key/salt are not configured.")


def _sha512_hash(value: str) -> str:
    return hashlib.sha512(value.encode("utf-8")).hexdigest()


def _normalize_phone(phone: str | None) -> str:
    if not phone:
        return ""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) > 10:
        digits = digits[-10:]
    return digits


def get_easebuzz_init_url() -> str:
    return settings.EASEBUZZ_INIT_URL


def create_order(
    *,
    user,
    amount,
    purpose: str = "",
    description: str = "",
    reference_type: str = "",
    reference_id: str = "",
    currency: str = "INR",
    metadata: dict | None = None,
) -> Order:
    return Order.objects.create(
        user=user,
        amount=amount,
        currency=currency,
        purpose=purpose or None,
        description=description or None,
        reference_type=reference_type or None,
        reference_id=reference_id or None,
        metadata=metadata,
    )


def create_payment_attempt(order: Order) -> PaymentTransaction:
    txnid = f"EB{order.id}{uuid.uuid4().hex[:12]}"
    return PaymentTransaction.objects.create(
        order=order,
        amount=order.amount,
        txnid=txnid,
        status="INITIATED",
    )


def build_easebuzz_payload(*, order: Order, payment_txn: PaymentTransaction, user, surl: str, furl: str) -> dict:
    _require_easebuzz_settings()

    first_name = user.first_name or user.username
    email = user.email or f"{user.username}@example.com"
    phone = ""
    profile = getattr(user, "profile", None)
    if profile:
        phone = _normalize_phone(profile.mobile_number)

    productinfo = order.description or order.purpose or f"Order {order.id}"

    payload = {
        "key": settings.EASEBUZZ_MERCHANT_KEY,
        "txnid": payment_txn.txnid,
        "amount": f"{order.amount:.2f}",
        "productinfo": productinfo,
        "firstname": first_name,
        "email": email,
        "phone": phone,
        "surl": surl,
        "furl": furl,
        "udf1": str(order.id),
        "udf2": order.reference_type or "",
        "udf3": order.reference_id or "",
        "udf4": "",
        "udf5": "",
        "udf6": "",
        "udf7": "",
        "udf8": "",
        "udf9": "",
        "udf10": "",
    }

    payload["hash"] = generate_request_hash(payload)
    return payload


def generate_request_hash(payload: dict) -> str:
    hash_sequence = [
        settings.EASEBUZZ_MERCHANT_KEY,
        payload.get("txnid", ""),
        payload.get("amount", ""),
        payload.get("productinfo", ""),
        payload.get("firstname", ""),
        payload.get("email", ""),
        payload.get("udf1", ""),
        payload.get("udf2", ""),
        payload.get("udf3", ""),
        payload.get("udf4", ""),
        payload.get("udf5", ""),
        payload.get("udf6", ""),
        payload.get("udf7", ""),
        payload.get("udf8", ""),
        payload.get("udf9", ""),
        payload.get("udf10", ""),
        settings.EASEBUZZ_SALT,
    ]
    return _sha512_hash("|".join(hash_sequence))


def verify_response_hash(data: dict) -> bool:
    expected_sequence = [
        settings.EASEBUZZ_SALT,
        data.get("status", ""),
        data.get("udf10", ""),
        data.get("udf9", ""),
        data.get("udf8", ""),
        data.get("udf7", ""),
        data.get("udf6", ""),
        data.get("udf5", ""),
        data.get("udf4", ""),
        data.get("udf3", ""),
        data.get("udf2", ""),
        data.get("udf1", ""),
        data.get("email", ""),
        data.get("firstname", ""),
        data.get("productinfo", ""),
        data.get("amount", ""),
        data.get("txnid", ""),
        settings.EASEBUZZ_MERCHANT_KEY,
    ]
    expected_hash = _sha512_hash("|".join(expected_sequence))
    return expected_hash == data.get("hash", "")


def apply_easebuzz_response(payment_txn: PaymentTransaction, data: dict) -> PaymentTransaction:
    status = (data.get("status") or "").upper()
    payment_txn.response_payload = data
    payment_txn.gateway_txn_id = data.get("easepayid") or data.get("transaction_id")

    if status == "SUCCESS":
        payment_txn.status = "SUCCESS"
        if payment_txn.order.status != "PAID":
            payment_txn.order.status = "PAID"
            payment_txn.order.paid_at = timezone.now()
            payment_txn.order.save(update_fields=["status", "paid_at", "updated_at"])
    else:
        payment_txn.status = "FAILED"
        payment_txn.error_message = data.get("error_Message") or data.get("error")
        if payment_txn.order.status == "PENDING":
            payment_txn.order.status = "FAILED"
            payment_txn.order.save(update_fields=["status", "updated_at"])

    payment_txn.save(update_fields=["status", "response_payload", "gateway_txn_id", "error_message", "updated_at"])
    return payment_txn
