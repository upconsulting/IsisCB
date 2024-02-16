from __future__ import unicode_literals
from django import template
from isisdata.models import *
from dateutil.relativedelta import relativedelta
from isisdata.templatetags.app_filters import *
from curation.utils import *

register = template.Library()

# this method also exists in app_filters; need to be consolidated
@register.filter
def get_uri(entry, tenant=None):
    if to_class_name(entry) == 'Authority':
        return (settings.URI_PREFIX if not tenant else settings.URI_HOST + settings.PORTAL_PREFIX + '/' + tenant + "/") + "authority/" + entry.id
    if to_class_name(entry) == 'Citation':
        return (settings.URI_PREFIX if not tenant else settings.URI_HOST + settings.PORTAL_PREFIX + '/' + tenant + "/") + "citation/" + entry.id
    return ""

@register.filter
def to_class_name(value):
    return value.__class__.__name__

@register.filter
def get_iso_date_string(date):
    return date.isoformat()

@register.filter
def add_css_placeholder(field, css_placeholder):
    parts = css_placeholder.split(';')
    placeholder = parts[1] if len(parts) >= 2 else ''
    css = parts[0]
    return field.as_widget(attrs={"placeholder": placeholder, "class": css})

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

@register.filter
def is_external_tenant(record, tenant):
    if not record:
        return True
    
    if (not record.owning_tenant and tenant) or (record.owning_tenant and not tenant):
        return True    

    return False if record.owning_tenant.id is tenant.id else True

@register.filter
def get_tenant(id):
    if id:
        return Tenant.objects.get(pk=id)
    return ""

@register.filter
def get_print_formatted_citation(id):
    return get_printlike_citation(id)

# This method figures out what page number each paginator button should link to given the current page number. Key is the url code for setting the page: 'page_citation'. 'sort_str' contains this key and the page number in question.
@register.filter
def set_bookshelf_page(link, sort_str):
    [key, page_number] = sort_str.split(":")
    if key in link:
        return re.sub(key + "=[0-9]+", key + "=" + str(page_number), link)
    else:
        new_link = link + "?" if "?" not in link else link + "&"
        return new_link + key + "=" + str(page_number)
    
# This method appends the search filters to the paginator buttons so that the correct queryset can be paginated for each page change
# @register.filter
# def set_paginator_search_filters(link, sort_str):