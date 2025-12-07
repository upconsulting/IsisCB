from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from django import template
from isisdata.models import *
from isisdata.templatetags.app_filters import *
import urllib.request, urllib.parse, urllib.error
import re

import logging

register = template.Library()
logger = logging.getLogger(__name__)

@register.filter
def get_authority_name(id):
    try:
        name = Authority.objects.values_list("name", flat=True).get(pk=id)
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
    qs = urllib.parse.parse_qsl(url)
    if not len(arg.split("=")) == 2:
        return url
    
    key = arg.split("=")[0]
    value = arg.split("=")[1]

    for para in qs:
        if para[0] == key and para[1] == value:
            qs.remove(para)
        # this is a hack but not sure a better way to do this at this point
        # if we didn't just delete the value with a '&' in it, then we need to quote the '&' to
        # make cases work in which a fact has an ampersand in the value
        # for some reason the facetting doesn't work if we don't do this
        if para in qs and "&" in para[1]:
            qs.remove(para)
            qs.append((para[0], urllib.parse.quote(para[1])))

    return "&".join([f"{para[0]}={para[1]}" for para in qs])

@register.filter
def add_selected_facet(url, facet):
    return (url + "&selected_facets=" + urllib.parse.unquote(facet)).replace("&&", "&")

@register.filter
def remove_query(url):
    # we will probably have the path prefix before the query string
    parsed_url = urllib.parse.urlparse(url)
    query_string = parsed_url.query   
    path = parsed_url.path      
    
    qs = urllib.parse.parse_qsl(query_string)
    for para in qs:
        if para[0] == "q":
            qs.remove(para)
        
    full_qs = "&".join([f"{para[0]}={para[1]}" for para in qs])
    return path + "?" + full_qs if path else full_qs


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
    return 'excluded_facets=citation_type:Review' in urllib.parse.unquote(url)

@register.filter
def is_limited_to_tech_culture(url):
    parsed_url = urllib.parse.urlparse(url)
    query_string = parsed_url.query   
    path = parsed_url.path      
    
    qs = urllib.parse.parse_qsl(query_string)
    for para in qs:
        if para[0] == "selected_facets" and para[1]=="citation_dataset_typed_names:Technology & Culture Bibliography":
            return True
    return False 

@register.filter
def limit_to_tech_culture_facet(url):
    return (url + "&selected_facets=citation_dataset_typed_names:Technology%20%26%20Culture%20Bibliography")


@register.filter
def are_stubs_excluded(url):
    return 'excluded_facets=citation_stub_record_status:SR' in urllib.parse.unquote(url)

@register.filter
def add_excluded_stub_record_status_facet(url, facet):
    facet_str = 'citation_stub_record_status:' + urllib.parse.quote(facet)
    if 'selected_facets=' + facet_str in url:
        url = url.replace('selected_facets=' + facet_str, '')
    url = url + '&excluded_facets=' + facet_str
    return url.replace('&&', '&')
