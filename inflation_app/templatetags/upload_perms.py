from django import template

register = template.Library()


@register.filter
def has_upload_permission(user, permission):
    if not user.is_authenticated:
        return False
    return user.groups.filter(
        id__in=permission.allowed_groups.values_list('id', flat=True)
    ).exists()
