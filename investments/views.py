from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q, Sum, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from investments.forms import InvestmentForm
from investments.services import InvestmentError, create_user_investment
from wallets.models import Wallet

from .models import InvestmentReturnLog, InvestmentScheme, UserInvestment


def _wallet_balances(user) -> dict:
    balances = dict(
        Wallet.objects.filter(user=user).values_list("wallet_type", "balance")
    )
    return {
        "personal": balances.get("PERSONAL", Decimal("0")),
        "investment": balances.get("INVESTMENT", Decimal("0")),
    }


@login_required
def funds_overview(request):
    balances = _wallet_balances(request.user)
    schemes = InvestmentScheme.objects.filter(is_active=True).order_by("name")

    now = timezone.now()
    active_investments = UserInvestment.objects.filter(
        user=request.user, status="ACTIVE", ends_at__gt=now
    ).select_related("scheme").annotate(total_returns=Sum("return_logs__return_amount")).order_by("-created_at")

    past_logs_prefetch = Prefetch(
        "return_logs",
        queryset=InvestmentReturnLog.objects.order_by("-date"),
    )
    completed_investments = (
        UserInvestment.objects.filter(user=request.user)
        .filter(Q(status="COMPLETED") | Q(ends_at__lte=now))
        .select_related("scheme")
        .prefetch_related(past_logs_prefetch)
        .annotate(
            total_returns=Sum("return_logs__return_amount"),
            return_count=Count("return_logs"),
        )
        .order_by("-ends_at")
    )

    context = {
        "title": "Funds",
        "heading": "Manage Your Funds",
        "message": "Track balances, investments, and returns.",
        "personal_balance": balances["personal"],
        "investment_balance": balances["investment"],
        "total_balance": balances["personal"] + balances["investment"],
        "schemes": schemes,
        "user_investments": active_investments,
        "completed_investments": completed_investments,
    }
    return render(request, "investments/funds.html", context)


@login_required
def scheme_detail(request, pk):
    scheme = get_object_or_404(InvestmentScheme, pk=pk, is_active=True)
    has_active_investment = UserInvestment.objects.filter(
        user=request.user,
        scheme=scheme,
        status="ACTIVE",
        ends_at__gt=timezone.now(),
    ).exists()

    if request.method == "POST":
        form = InvestmentForm(request.POST, scheme=scheme)
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            try:
                create_user_investment(request.user, scheme, amount)
            except InvestmentError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(
                    request,
                    "Investment created successfully. Your first daily return has been credited to your investment wallet.",
                )
                return redirect("funds")
    else:
        form = InvestmentForm(scheme=scheme)

    return render(
        request,
        "investments/scheme_detail.html",
        {
            "scheme": scheme,
            "form": form,
            "has_active_investment": has_active_investment,
        },
    )
