# signals.py
from django.db.models.signals import post_save
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import UploadPermission


def create_upload_permission(sender, instance, created, **kwargs):
    if created:
        content_type = ContentType.objects.get_for_model(instance)
        Permission.objects.get_or_create(
            codename=f'can_upload_{instance.code}',
            name=f'Can upload {instance.label}',
            content_type=content_type,
        )


post_save.connect(create_upload_permission, sender=UploadPermission)

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import PriceObservation
from .handlers import invalidate_dashboard_cache

@receiver([post_save, post_delete], sender=PriceObservation)
def handle_price_observation_change(sender, instance, **kwargs):
    """
    Only invalidate relevant dashboard keys when a PriceObservation is updated or deleted.
    """
    invalidate_dashboard_cache(
        product_id=instance.product_id,
        region_id=instance.region_id,
        district_id=instance.district_id,
        date=str(instance.date)
    )
