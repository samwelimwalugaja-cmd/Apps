from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Member

User = get_user_model()

@receiver(post_save, sender=User)
def create_member(sender, instance, created, **kwargs):
    if created:
        Member.objects.create(
            email=instance.email,
            first_name=instance.first_name or "",
            last_name=instance.last_name or ""
        )