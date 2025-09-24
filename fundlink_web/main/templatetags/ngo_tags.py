from django import template

register = template.Library()

@register.filter
def has_ngo(user):
    return hasattr(user, 'ngo') and user.ngo is not None
