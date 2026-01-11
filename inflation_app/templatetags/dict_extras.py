from django import template

register = template.Library()

@register.filter
def dict_get(d, key):
    """Get a value from a dict by key in templates."""
    if d and key:
        return d.get(key)
    return None
