# Create your models here.
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class RequestLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)

    ip_address = models.GenericIPAddressField()
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="request_logs",
    )

    method = models.CharField(max_length=10)
    path = models.CharField(max_length=512)

    query_params = models.JSONField(null=True, blank=True)

    status_code = models.PositiveSmallIntegerField()
    duration_ms = models.PositiveIntegerField()

    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.ip_address} → {self.path}"
