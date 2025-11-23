from datetime import date as date_cls

from django.core.management.base import BaseCommand
from django.utils import timezone

from investments.services import credit_daily_returns


class Command(BaseCommand):
    help = "Credit current day's returns for all active investments to investment wallets."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="ISO date (YYYY-MM-DD). Defaults to today in server timezone.",
        )

    def handle(self, *args, **options):
        date_option = options.get("date")
        if date_option:
            try:
                target_date = date_cls.fromisoformat(date_option)
            except ValueError:
                self.stderr.write(
                    self.style.ERROR("Invalid date format. Use YYYY-MM-DD.")
                )
                return
        else:
            target_date = timezone.localdate()

        credited = credit_daily_returns(for_date=target_date)
        message = f"Credited {credited} daily return(s) for {target_date}."
        if credited:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stdout.write(message)
