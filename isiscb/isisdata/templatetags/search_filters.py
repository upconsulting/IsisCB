from django import template
from isisdata.models import *
import base64, urllib

from urllib import quote
import codecs

register = template.Library()


@register.filter
def get_nr_of_citations(authority):
    return ACRelation.objects.filter(authority=authority, citation__public=True, public=True).distinct('citation_id').count()


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
def include_facet(url, arg):
    return url.replace(arg, "").replace("&&", "&")


@register.filter
def create_exclude_facet_string(facet, field):
    return 'excluded_facets=' + field + ':' + quote(codecs.encode(facet,'utf-8'))
