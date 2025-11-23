from decimal import Decimal

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import Wallet


@login_required
def funds(request):
    wallet_balances = dict(
        Wallet.objects.filter(user=request.user).values_list("wallet_type", "balance")
    )

    personal_balance = wallet_balances.get("PERSONAL", Decimal("0"))
    investment_balance = wallet_balances.get("INVESTMENT", Decimal("0"))

    context = {
        "title": "Funds",
        "heading": "Manage Your Funds",
        "message": "Track balances and transactions across your wallets.",
        "personal_balance": personal_balance,
        "investment_balance": investment_balance,
        "total_balance": personal_balance + investment_balance,
    }
    return render(request, "wallets/funds.html", context)
