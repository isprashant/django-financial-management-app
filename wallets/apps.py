from django.apps import AppConfig


class WalletsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'wallets'

    def ready(self):
        try:
            import wallets.signals  # noqa: F401
        except ImportError:
            pass
