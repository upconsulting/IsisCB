from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

import urllib2

register = template.Library()


@register.filter(name='filter_unresolved')
def filter_unresolved(queryset):
    return queryset.filter(processed=False)
