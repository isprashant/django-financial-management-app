from django.core.management.base import BaseCommand

from referrals.models import ReferralCode
from referrals.services import ensure_referral_code
from users.models import CustomUser


class Command(BaseCommand):
    help = "Ensure every user has a referral code and slug."

    def handle(self, *args, **options):
        created = 0
        for user in CustomUser.objects.all():
            pre_exists = ReferralCode.objects.filter(user=user).exists()
            ensure_referral_code(user)
            post_exists = ReferralCode.objects.filter(user=user).exists()
            if not pre_exists and post_exists:
                created += 1

        message = "All users already have referral codes."
        if created:
            message = f"Created {created} referral codes."
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stdout.write(message)
