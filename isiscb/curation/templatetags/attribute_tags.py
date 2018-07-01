from django import template
from isisdata.models import *

register = template.Library()

@register.filter()
def get_dates(attr_ids):
    if not attr_ids:
        return None
    if not isinstance(attr_ids, list):
        attr_ids = [attr_ids]
    return [a for a in Attribute.objects.all().filter(pk__in=attr_ids) if type(a.value.get_child_class()) in [DateTimeValue, DateValue, ISODateValue, ISODateRangeValue]]
