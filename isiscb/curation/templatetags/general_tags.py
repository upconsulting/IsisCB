from __future__ import unicode_literals
from django import template
from isisdata.models import *
from dateutil.relativedelta import relativedelta

register = template.Library()

# this method also exists in app_filters; need to be consolidated
@register.filter
def get_uri(entry, tenant=None):
    if to_class_name(entry) == 'Authority':
        return (settings.URI_PREFIX if not tenant else settings.URI_HOST + "portal/" + tenant + "/") + "authority/" + entry.id
    if to_class_name(entry) == 'Citation':
        return (settings.URI_PREFIX if not tenant else settings.URI_HOST + "portal/" + tenant + "/") + "citation/" + entry.id
    return ""

@register.filter
def to_class_name(value):
    return value.__class__.__name__

@register.filter
def get_iso_date_string(date):
    return date.isoformat()

@register.filter
def add_popover(field, css_placeholder_text):
    parts = css_placeholder_text.split(';')
    placeholder = parts[1] if len(parts) >= 2 else ''
    text = parts[2] if len(parts) >= 3 else ''
    orientation = parts[3] if len(parts) >= 4 else 'right'
    css = parts[0]

    return field.as_widget(attrs={"class": css, "placeholder": placeholder, \
                    "data-toggle": "popover", "data-trigger":"hover", \
                    "data-placement": orientation, "data-content": text})

@register.filter(name='field_type')
def field_type(field):
    return field.field.widget.__class__.__name__

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
