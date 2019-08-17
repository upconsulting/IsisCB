from django import template
from isisdata.models import *

register = template.Library()


@register.filter
def get_uri(entry):
    if to_class_name(entry) == 'Authority':
        return settings.URI_PREFIX + "authority/" + entry.id
    if to_class_name(entry) == 'Citation':
        return settings.URI_PREFIX + "citation/" + entry.id
    return ""


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
