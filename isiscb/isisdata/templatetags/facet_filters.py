from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from django import template
from isisdata.models import *
from isisdata.templatetags.app_filters import *
import urllib.request, urllib.parse, urllib.error
import re

register = template.Library()

@register.filter
def get_authority_name(id):
    try:
        authority = Authority.objects.get(id=id)
        name = authority.name
    except:
        name = id
    return name

@register.filter
def set_excluded_facets(url, available_facets):
    facets = list(available_facets)
    exclude_str = ""
    for facet in facets:
        facet_tuple = tuple(facet)
        if 'selected_facets=citation_type:'+facet_tuple[0] not in url:
            exclude_str += 'excluded_facets=citation_type:' + facet_tuple[0] + "&"
    return (url+ '&' + exclude_str).replace("&&", "&")

@register.filter
def remove_url_part(url, arg):
    return url.replace(arg, "").replace("&&", "&")

@register.filter
def add_selected_facet(url, facet):
    return (url + "&selected_facets=" + urllib.parse.unquote(facet)).replace("&&", "&")

@register.filter
def add_facet_or_operator(url):
    op = 'facet_operators=type:or'
    if op not in url:
        url = url + '&' + op
    return url.replace('&&', '&')

@register.filter
def add_excluded_citation_type_facet(url, facet):
    facet_str = 'citation_type:' + urllib.parse.quote(facet)
    if 'selected_facets=' + facet_str in url:
        url = url.replace('selected_facets=' + facet_str, '')
    url = url + '&excluded_facets=' + facet_str
    return url.replace('&&', '&')

@register.filter
def add_excluded_facet(url, facet):
    if 'selected_facets=' + facet in url:
        url = url.replace('selected_facets=' + facet, '')
    url = url + '&excluded_facets=' + facet
    return url.replace('&&', '&')

@register.filter
def remove_all_type_facets(url, facet_type):
    url = re.sub(r"selected_facets=" + facet_type + ":.+?&", "", url).replace('&&', '&')
    return re.sub(r"excluded_facets=" + facet_type + ":.+?&", "", url).replace('&&', '&')

@register.filter
def create_facet_with_field(facet, field):
    return field + ":" + facet

@register.filter
def are_reviews_excluded(url):
    return 'excluded_facets=citation_type:Review' in url

@register.filter
def are_stubs_excluded(url):
    return 'excluded_facets=citation_stub_record_status:SR' in url

@register.filter
def add_excluded_stub_record_status_facet(url, facet):
    facet_str = 'citation_stub_record_status:' + urllib.parse.quote(facet)
    if 'selected_facets=' + facet_str in url:
        url = url.replace('selected_facets=' + facet_str, '')
    url = url + '&excluded_facets=' + facet_str
    return url.replace('&&', '&')
