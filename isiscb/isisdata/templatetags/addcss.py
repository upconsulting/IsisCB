from __future__ import unicode_literals
from django import template
register = template.Library()

@register.filter(name='addcss')
def addcss(field, css):
    if type(field) is str:
        return field
    parts = css.split(';')
    placeholder = parts[1] if len(parts) == 2 else ''
    css = parts[0]

    return field.as_widget(attrs={"class": css, "placeholder": placeholder})

@register.filter
def get_alert_class(level):
    alert_classes = {
        'INFO': 'info',
        'WARN': 'warning',
        'DANGER': 'danger'
    }
    if level in alert_classes:
        return alert_classes[level]
    return 'info'