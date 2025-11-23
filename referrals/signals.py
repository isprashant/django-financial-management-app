from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .services import ensure_referral_code, handle_successful_signup

User = settings.AUTH_USER_MODEL


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_referral_code_for_new_user(sender, instance, created, **kwargs):
    if created:
        ensure_referral_code(instance)
