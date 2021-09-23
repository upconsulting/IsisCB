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
def get_page_range(paginator, current_page):
    start_page = current_page - 5 if current_page - 5 > 1 else 1
    end_page = current_page + 5 if paginator.num_pages > current_page + 5 else paginator.num_pages + 1
    return range(start_page, end_page)

@register.filter
def get_data_parts(review_string):
    return review_string.split("##")

@register.filter
def remove_range_filter(url):
    return re.sub(r"(&range_filters=.*?)($|&)", r"\2", url)
