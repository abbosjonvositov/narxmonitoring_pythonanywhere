from django.contrib import admin
from django.db.models import Count
from django.utils.safestring import mark_safe
from .models import RequestLog


@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp",
        "ip_address",
        "user",
        "method",
        "path",
        "status_code",
        "duration_ms",
    )

    list_filter = ("method", "status_code", "user", "timestamp")
    search_fields = ("ip_address", "path", "user__username", "user_agent")
    readonly_fields = [f.name for f in RequestLog._meta.fields]

    change_list_template = "admin/traffic/requestlog_changelist.html"  # 👈 custom template

    def changelist_view(self, request, extra_context=None):
        # Top 10 paths
        top_paths = (
            RequestLog.objects.values("path")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        extra_context = extra_context or {}
        extra_context["top_paths"] = top_paths

        # Top 10 IPs
        top_ips = (
            RequestLog.objects.values("ip_address")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        extra_context["top_ips"] = top_ips

        # Top 10 users
        top_users = (
            RequestLog.objects.values("user__username")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        extra_context["top_users"] = top_users

        return super().changelist_view(request, extra_context=extra_context)
