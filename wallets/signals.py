from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from wallets.services import ensure_wallets_for_user

User = settings.AUTH_USER_MODEL


@receiver(post_save, sender=User)
def create_wallets_for_new_user(sender, instance, created, **kwargs):
    if created:
        ensure_wallets_for_user(instance)
