from django import template
from isisdata.models import *
import base64, urllib
from app_filters import *
from django.core.urlresolvers import reverse

register = template.Library()

@register.filter
def get_nr_of_citations(authority):
    return ACRelation.objects.filter(authority=authority, citation__public=True).distinct('citation_id').count()

@register.filter
def encode_query(query):
    if not query:
        return ''
    return urllib.quote(query)

@register.filter
def decode_query(query):
    if not query:
        return ''
    return urllib.unquote(query)

@register.filter
def create_label(entry):
    if to_class_name(entry) == 'Authority':
        return entry.name
    if to_class_name(entry) == 'Citation':
        return bleach_safe(get_title(entry))
    return 'No label'

@register.filter
def get_url(entry):
    type = 'index'

    if to_class_name(entry) == 'Authority':
        type = 'authority'
    if to_class_name(entry) == 'Citation':
        type = 'citation'

    return reverse(type, args=[entry.id])
