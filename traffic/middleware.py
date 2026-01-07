import time
from .models import RequestLog


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        duration_ms = int((time.time() - start) * 1000)

        # Skip logging admin requests
        if not request.path.startswith("/admin/"):
            RequestLog.objects.create(
                ip_address=self.get_ip(request),
                user=request.user if request.user.is_authenticated else None,
                method=request.method,
                path=request.path,
                query_params=request.GET.dict(),
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )

        return response

    def get_ip(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0]
        return request.META.get("REMOTE_ADDR")
