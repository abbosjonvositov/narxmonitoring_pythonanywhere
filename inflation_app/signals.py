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
