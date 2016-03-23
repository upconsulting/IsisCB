from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

import urllib2

register = template.Library()


@register.filter(name='build_get_params')
def build_get_params(draftauthority):
    get_string = u'?'
    param_fields = [
        ('name', 'name'),
        ('name_first', 'name_first'),
        ('name_last', 'name_last'),
        ('name_suffix', 'name_suffix'),
        ('type_controlled', 'type_controlled'),
    ]
    parameters = ['{0}={1}'.format(field, urllib2.quote(getattr(draftauthority, attr)))
                  for attr, field in param_fields
                  if getattr(draftauthority, attr)]
    get_string += u'&'.join(parameters)
    return get_string
