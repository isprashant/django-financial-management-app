from decimal import Decimal
from urllib.parse import quote

from django.conf import settings
from django.shortcuts import render
from django.urls import reverse

from referrals.services import ensure_referral_code
from rewards.models import RewardItem
from users.models import UserPointsSnapshot
from plans.models import SignupPlan, UserSubscription
from plans.services import PlanPurchaseError, activate_signup_plan
from wallets.models import Wallet


def index(request):
    return render(request, "ui_gsm/index.html")


def about(request):
    return render(
        request,
        "ui_gsm/about.html",
        {
            "title": "About GSM",
            "heading": "About GSM",
            "message": "Learn more about the GSM platform.",
        },
    )




def earn(request):
    return render(
        request,
        "ui_gsm/earn.html",
        {
            "title": "Start Earning",
            "heading": "Start earning money",
            "message": "Explore opportunities to earn within GSM.",
        },
    )


def join(request):
    plans = SignupPlan.objects.filter(is_active=True).order_by("join_fee")
    subscription = None
    personal_balance = None
    success_message = None
    error_message = None
    current_plan_id = None

    if request.user.is_authenticated:
        subscription = UserSubscription.objects.filter(user=request.user).first()
        if subscription:
            current_plan_id = subscription.plan_id
        personal_wallet, _ = Wallet.objects.get_or_create(
            user=request.user, wallet_type="PERSONAL", defaults={"balance": Decimal("0.00")}
        )
        personal_balance = personal_wallet.balance

        if request.method == "POST":
            plan_id = request.POST.get("plan_id")
            try:
                activate_signup_plan(request.user, plan_id)
                subscription = UserSubscription.objects.get(user=request.user)
                success_message = "Plan activated successfully using your personal wallet."
            except PlanPurchaseError as e:
                error_message = str(e)
            except SignupPlan.DoesNotExist:
                error_message = "Selected plan is not available."

    return render(
        request,
        "ui_gsm/join.html",
        {
            "title": "Join GSM",
            "heading": "Choose your plan",
            "message": "Pick a signup plan to start earning on tasks.",
            "plans": plans,
            "subscription": subscription,
            "personal_balance": personal_balance,
            "success_message": success_message,
            "error_message": error_message,
            "current_plan_id": current_plan_id,
        },
    )


def invite(request):
    invite_code = None
    invite_link = None
    qr_url = None

    if request.user.is_authenticated:
        code_obj = ensure_referral_code(request.user)
        invite_code = code_obj.code
        base_url = getattr(settings, "REFERRAL_BASE_URL", "").rstrip("/")
        path = reverse("referrals:referral_redirect", args=[code_obj.slug])
        if not base_url:
            base_url = request.build_absolute_uri("/").rstrip("/")
        invite_link = f"{base_url}{path}"
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={quote(invite_link)}"

    return render(
        request,
        "ui_gsm/invite.html",
        {
            "title": "Invite a Friend",
            "heading": "Invite friend",
            "message": "Send invites and grow the community.",
            "invite_code": invite_code,
            "invite_link": invite_link,
            "qr_url": qr_url,
        },
    )


def growth(request):
    rewards = RewardItem.objects.filter(is_active=True).order_by("-created_at")
    points_balance = None
    if request.user.is_authenticated:
        snapshot, _ = UserPointsSnapshot.objects.get_or_create(
            user=request.user, defaults={"active_points": Decimal("0.00")}
        )
        points_balance = snapshot.active_points
    return render(
        request,
        "ui_gsm/growth.html",
        {
            "title": "Growth Points",
            "heading": "Redeem Rewards",
            "message": "Use your points to redeem exclusive rewards.",
            "rewards": rewards,
            "points_balance": points_balance,
        },
    )
