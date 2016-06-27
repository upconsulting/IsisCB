from django import template
from isisdata.models import *
from isisdata.templatetags.app_filters import *
import urllib

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
    return (url + "&selected_facets=citation_type:" + urllib.unquote(facet)).replace("&&", "&")

@register.filter
def add_facet_or_operator(url):
    op = 'facet_operators=type:or'
    if op not in url:
        url = url + '&' + op
    return url.replace('&&', '&')

@register.filter
def add_excluded_citation_type_facet(url, facet):
    facet_str = 'citation_type:' + urllib.quote(facet)
    if 'selected_facets=' + facet_str in url:
        url = url.replace('selected_facets=' + facet_str, '')
    url = url + '&excluded_facets=' + facet_str
    return url.replace('&&', '&')
