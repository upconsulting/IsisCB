from django import template
from isisdata.models import *
import base64, urllib

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
