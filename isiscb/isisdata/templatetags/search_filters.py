from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from django import template
from isisdata.models import *
import base64, urllib.request, urllib.parse, urllib.error

from urllib.parse import quote
import codecs, re

from haystack.query import EmptySearchQuerySet, SearchQuerySet

register = template.Library()


@register.filter
def get_nr_of_citations(authority):
    sqs =SearchQuerySet().models(Citation).all().exclude(public="false") \
            .filter_or(author_ids=authority.id).filter_or(contributor_ids=authority.id) \
            .filter_or(editor_ids=authority.id).filter_or(subject_ids=authority.id).filter_or(institution_ids=authority.id) \
            .filter_or(category_ids=authority.id).filter_or(advisor_ids=authority.id).filter_or(translator_ids=authority.id) \
            .filter_or(publisher_ids=authority.id).filter_or(school_ids=authority.id).filter_or(meeting_ids=authority.id) \
            .filter_or(periodical_ids=authority.id).filter_or(book_series_ids=authority.id).filter_or(time_period_ids=authority.id) \
            .filter_or(geographic_ids=authority.id).filter_or(about_person_ids=authority.id).filter_or(other_person_ids=authority.id)
    return sqs.count()
    #return ACRelation.objects.filter(authority=authority, citation__public=True, public=True).distinct('citation_id').count()


@register.filter
def encode_query(query):
    if not query:
        return ''
    return urllib.parse.quote(query)


@register.filter
def decode_query(query):
    if not query:
        return ''
    return urllib.parse.unquote(query)


@register.filter
def include_facet(url, arg):
    return url.replace(arg, "").replace("&&", "&")


@register.filter
def create_exclude_facet_string(facet, field):
    return 'excluded_facets=' + field + ':' + quote(codecs.encode(facet,'utf-8'))

@register.filter
def format_query(query):
    author_match = re.match("\(author_ids:(CBA[0-9]{9}) OR contributor_ids:CBA", query)
    subject_match = re.match("\(subject_ids:(CBA[0-9]{9}) OR category_ids:CBA", query)
    publisher_match = re.match("\(publisher_ids:(CBA[0-9]{9}) OR periodical_ids:CBA", query)
    all_results = re.match("\*", query)
    authority_type_label_map = {
        'CO': ' label-concepts',
        'TI': ' label-times',
        'GE': ' label-places',
        'PE': ' label-people',
        'IN': ' label-institutions',
        'SE': ' label-institutions',
        'PU': ' label-institutions',
        'CT': ' label-default',
        'CW': ' label-default',
        'CR': ' label-default',
        'BL': ' label-default',
    }

    if author_match or subject_match or publisher_match:
        if author_match:
            authority_id = author_match.group(1)
        elif subject_match:
            authority_id = subject_match.group(1)
        else:
            authority_id = publisher_match.group(1)
            
        try:
            authority = Authority.objects.get(id=authority_id)
            name = authority.name
            authority_type = authority.type_controlled
        except:
            name = authority_id
            authority_type = "CO"
        
        if authority_type_label_map[authority_type]:
            return mark_safe('<span class="h4" style="margin: 0">' + name + '&nbsp<span class="label' + authority_type_label_map[authority_type] + '">' + authority.get_type_controlled_display() + '</span></span>')
        else:
            return mark_safe('<span class="h4" style="margin: 0">' + name + '&nbsp<span class="label' + authority_type_label_map[authority.CONCEPT] + '">' + authority.get_type_controlled_display() + '</span></span>') 
    elif all_results:
        return mark_safe('<span class="h4" style="margin: 0">everything</span>')
    else:
        return mark_safe('<span class="h4" style="margin: 0">"' + query + '"</span>')

@register.filter
def format_query_preamble(query):
    author_match = re.match("\(author_ids:(CBA[0-9]{9}) OR contributor_ids:CBA", query)
    subject_match = re.match("\(subject_ids:(CBA[0-9]{9}) OR category_ids:CBA", query)
    publisher_match = re.match("\(publisher_ids:(CBA[0-9]{9}) OR periodical_ids:CBA", query)
    all_results = re.match("\*", query)

    if author_match or subject_match or publisher_match:
        return mark_safe('<strong style="font-size: 1.4em; color: #337ab7">items related to: </strong>')
    elif all_results:
        return mark_safe('<strong style="font-size: 1.4em; color: #337ab7">items related to: </strong>')
    else:
        return mark_safe('<strong style="font-size: 1.4em; color: #337ab7">search: </strong>')

@register.filter
def count_relations(relations, type):
    count = 0
    for relation in relations:
        if relation['type'] == type:
            count += 1
    return count
    
