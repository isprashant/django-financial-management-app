from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile

User = settings.AUTH_USER_MODEL


@receiver(post_save, sender=User)
def create_profile_for_user(sender, instance, created, **kwargs):
    if created:
        mobile_placeholder = f"auto-{instance.id}"
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                "mobile_number": mobile_placeholder,
                "full_name": instance.get_full_name() or instance.username,
                "withdrawal_method": "",
                "withdrawal_details": "",
            },
        )
