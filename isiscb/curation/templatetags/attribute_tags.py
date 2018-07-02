from django import template
from isisdata.models import *

register = template.Library()

@register.filter()
def get_dates(obj):
    attrs = Authority.objects.get(pk=obj['id']).attributes.all()
    if not attrs:
        return None

    return [a for a in attrs if type(a.value.get_child_class()) in [DateTimeValue, DateValue, ISODateValue, ISODateRangeValue]]

@register.filter()
def get_linkeddata(obj):
    return Authority.objects.get(pk=obj['id']).linkeddata_entries.all()

@register.filter()
def get_attributes(obj):
    attrs = Authority.objects.get(pk=obj['id']).attributes.all()
    if not attrs:
        return None

    return [a for a in attrs if type(a.value.get_child_class()) not in [DateTimeValue, DateValue, ISODateValue, ISODateRangeValue]]

@register.filter()
def get_acr_count(obj):
    return Authority.objects.get(pk=obj['id']).acrelations.count()
