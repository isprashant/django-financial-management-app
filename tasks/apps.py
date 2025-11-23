from django.apps import AppConfig


class TasksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tasks"

    def ready(self):
        """
        Import signal handlers so that tasks are created automatically whenever
        new Movie or PropertyListing instances are saved.
        """
        try:
            import tasks.signals  # noqa: F401
        except ImportError:
            # Signals module is optional while running certain commands (e.g. migrations)
            pass
