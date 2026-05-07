from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .models import Order, PaymentTransaction
from .services import (
    apply_easebuzz_response,
    build_easebuzz_payload,
    create_payment_attempt,
    get_easebuzz_init_url,
    verify_response_hash,
)


@login_required
def start_payment(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id, user=request.user)

    if order.status == "PAID":
        return render(
            request,
            "payments/result.html",
            {
                "order": order,
                "status": "Success",
                "message": "This order is already paid.",
            },
        )

    payment_txn = create_payment_attempt(order)
    callback_url = request.build_absolute_uri(reverse("payments:callback"))
    payload = build_easebuzz_payload(
        order=order,
        payment_txn=payment_txn,
        user=request.user,
        surl=callback_url,
        furl=callback_url,
    )

    payment_txn.request_payload = payload
    payment_txn.save(update_fields=["request_payload", "updated_at"])

    return render(
        request,
        "payments/redirect.html",
        {
            "order": order,
            "post_url": get_easebuzz_init_url(),
            "payload": payload,
        },
    )


@csrf_exempt
def easebuzz_callback(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request.")

    data = request.POST.dict()
    txnid = data.get("txnid")
    if not txnid:
        return HttpResponseBadRequest("Missing transaction id.")

    payment_txn = get_object_or_404(PaymentTransaction, txnid=txnid)

    if not verify_response_hash(data):
        payment_txn.status = "FAILED"
        payment_txn.error_message = "Invalid hash response."
        payment_txn.response_payload = data
        payment_txn.save(update_fields=["status", "error_message", "response_payload", "updated_at"])
        return HttpResponseBadRequest("Invalid hash response.")

    payment_txn = apply_easebuzz_response(payment_txn, data)
    status = "Success" if payment_txn.status == "SUCCESS" else "Failed"
    message = "Payment completed successfully." if payment_txn.status == "SUCCESS" else "Payment failed."

    return render(
        request,
        "payments/result.html",
        {
            "order": payment_txn.order,
            "status": status,
            "message": message,
            "gateway_reference": payment_txn.gateway_txn_id,
        },
    )

@login_required
def order_detail(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, "payments/order_detail.html", {"order": order})


@login_required
def order_status(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    latest_txn = order.transactions.order_by("-created_at").first()
    return JsonResponse(
        {
            "id": order.id,
            "status": order.status,
            "amount": str(order.amount),
            "currency": order.currency,
            "paid_at": order.paid_at.isoformat() if order.paid_at else None,
            "gateway": latest_txn.gateway if latest_txn else None,
            "gateway_txn_id": latest_txn.gateway_txn_id if latest_txn else None,
            "txnid": latest_txn.txnid if latest_txn else None,
        }
    )
