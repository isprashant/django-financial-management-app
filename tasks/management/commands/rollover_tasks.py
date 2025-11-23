from __future__ import annotations

from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from tasks.services import rollover_pending_tasks


class Command(BaseCommand):
    help = (
        "Move pending tasks from previous dates to the provided date "
        "(defaults to today) so they remain available for users."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Target date in YYYY-MM-DD format. Defaults to today.",
        )

    def handle(self, *args, **options):
        target_date_str = options.get("date")
        target_date = None

        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            except ValueError as exc:
                raise CommandError(
                    f"Invalid date '{target_date_str}'. Use YYYY-MM-DD."
                ) from exc

        updated_count = rollover_pending_tasks(target_date=target_date)
        self.stdout.write(
            self.style.SUCCESS(f"Rolled over {updated_count} pending task(s).")
        )
