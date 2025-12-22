from decimal import Decimal
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render
from django.urls import reverse

from referrals.models import Referral
from referrals.services import ensure_referral_code
from rewards.models import RewardItem
from users.models import UserPointsSnapshot
from plans.models import SignupPlan, UserSubscription
from plans.services import PlanPurchaseError, activate_signup_plan
from wallets.models import Wallet, WalletTransaction


def index(request):
    return render(request, "ui_gsm/index.html")


def about(request):
    return render(
        request,
        "ui_gsm/about.html",
        {
            "title": "About KSB",
            "heading": "About KSB",
            "message": "Learn more about the KSB platform.",
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


@login_required(login_url="/login/")
def invite(request):
    invite_code = None
    invite_link = None
    qr_url = None
    team_size = 0
    team_subscription_count = 0
    team_personal_deposits = Decimal("0.00")
    plan_widgets = []

    code_obj = ensure_referral_code(request.user)
    invite_code = code_obj.code
    base_url = getattr(settings, "REFERRAL_BASE_URL", "").rstrip("/")
    path = reverse("referrals:referral_redirect", args=[code_obj.slug])
    if not base_url:
        base_url = request.build_absolute_uri("/").rstrip("/")
    invite_link = f"{base_url}{path}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={quote(invite_link)}"

    team_member_ids = list(
        Referral.objects.filter(referrer=request.user, referred__isnull=False).values_list("referred_id", flat=True)
    )
    team_size = len(team_member_ids)

    if team_member_ids:
        team_subscription_count = UserSubscription.objects.filter(user_id__in=team_member_ids).count()
        deposit_agg = (
            WalletTransaction.objects.filter(
                wallet__wallet_type="PERSONAL",
                wallet__user_id__in=team_member_ids,
                txn_type="DEPOSIT",
                is_credit=True,
            ).aggregate(total=Sum("amount"))
        )
        team_personal_deposits = deposit_agg["total"] or Decimal("0.00")
        plan_counts = {
            row["plan_id"]: row["total"]
            for row in UserSubscription.objects.filter(user_id__in=team_member_ids)
            .values("plan_id")
            .annotate(total=Count("id"))
        }
    else:
        plan_counts = {}

    plans = SignupPlan.objects.filter(is_active=True).order_by("join_fee")
    for plan in plans:
        plan_widgets.append({"plan": plan, "joined_count": plan_counts.get(plan.id, 0)})

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
            "team_size": team_size,
            "team_subscription_count": team_subscription_count,
            "team_personal_deposits": team_personal_deposits,
            "plan_widgets": plan_widgets,
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


@login_required(login_url="/login/")
def team_overview(request):
    """
    Show only the current user's direct referrals with their own team size and revenue.
    """
    referrals = Referral.objects.filter(referrer=request.user, referred__isnull=False).select_related("referred")
    direct_member_ids = {ref.referred_id for ref in referrals if ref.referred_id}

    deposit_totals = {}
    # Downline per direct member
    downline_refs = Referral.objects.filter(referrer_id__in=direct_member_ids, referred__isnull=False).values(
        "referrer_id", "referred_id"
    )
    downline_map = {}
    all_downline_ids = set()
    for row in downline_refs:
        downline_map.setdefault(row["referrer_id"], set()).add(row["referred_id"])
        all_downline_ids.add(row["referred_id"])

    if all_downline_ids:
        deposit_rows = (
            WalletTransaction.objects.filter(
                wallet__wallet_type="PERSONAL",
                wallet__user_id__in=all_downline_ids,
                txn_type="DEPOSIT",
                is_credit=True,
            )
            .values("wallet__user_id")
            .annotate(total=Sum("amount"))
        )
        deposit_totals = {row["wallet__user_id"]: row["total"] or Decimal("0.00") for row in deposit_rows}

    team_rows = []
    for ref in referrals:
        member_downline = downline_map.get(ref.referred_id, set())
        revenue = sum(deposit_totals.get(member_id, Decimal("0.00")) for member_id in member_downline)
        team_rows.append(
            {
                "referred": ref.referred,
                "team_size": len(member_downline),
                "team_revenue": revenue,
            }
        )

    team_rows.sort(key=lambda row: row["team_revenue"], reverse=True)

    return render(
        request,
        "ui_gsm/team_overview.html",
        {
            "title": "Team Overview",
            "heading": "Team Performance",
            "message": "Referral team sizes and revenue.",
            "team_rows": team_rows,
        },
    )
