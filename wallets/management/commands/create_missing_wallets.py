from django.core.management.base import BaseCommand

from wallets.services import backfill_wallets_for_existing_users


class Command(BaseCommand):
    help = "Create missing personal/investment wallets for all existing users."

    def handle(self, *args, **options):
        created = backfill_wallets_for_existing_users()
        self.stdout.write(self.style.SUCCESS(f"Created {created} wallet(s)."))
