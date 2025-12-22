from django.core.management.base import BaseCommand

from tasks.services import backfill_tasks_for_users_without_tasks


class Command(BaseCommand):
    help = "Create tasks for existing users who currently have no tasks (movies/properties)."

    def handle(self, *args, **options):
        created = backfill_tasks_for_users_without_tasks()
        self.stdout.write(self.style.SUCCESS(f"Created {created} task(s) for users without tasks."))
