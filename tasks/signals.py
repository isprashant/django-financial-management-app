from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from tasks.services import create_tasks_for_new_user

User = settings.AUTH_USER_MODEL


@receiver(post_save, sender=User)
def provision_tasks_for_new_user(sender, instance, created, **kwargs):
    if created:
        create_tasks_for_new_user(instance)
