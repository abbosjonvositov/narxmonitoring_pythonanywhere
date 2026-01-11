# myapp/context_processors.py
from django.conf import settings


def language_name_map(request):
    """
    Adds LANGUAGE_NAME_MAP to every template context.
    """
    return {
        "LANGUAGE_NAME_MAP": getattr(settings, "LANGUAGE_NAME_MAP", {})
    }
