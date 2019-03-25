from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

import urllib2

from isisdata.models import *

register = template.Library()


@register.filter(name='filter_unresolved')
def filter_unresolved(queryset):
    return queryset.filter(processed=False)


@register.filter(name='filter_unresolved_acrelation')
def filter_unresolved_acrelation(queryset):
    return queryset.filter(authority__processed=False)

@register.filter
def get_from_dict(dictionary, key):
    return dictionary.get(key)

@register.filter
def get_periodical_or_book_series(citation):
    rtypes = [ACRelation.PERIODICAL, ACRelation.BOOK_SERIES]
    atype_display = dict(ACRelation.TYPE_CHOICES)
    relations = ACRelation.objects.filter(citation_id=citation.id, type_controlled__in=rtypes).values('authority__name', 'authority__type_controlled')
    return ', '.join(map(lambda obj: '%s' % (obj.get('authority__name', '')), relations))

@register.filter
def get_book_if_chapter(citation):
    if citation.type_controlled != Citation.CHAPTER:
        return None

    relations = CCRelation.objects.filter(object=citation.id, type_controlled=CCRelation.INCLUDES_CHAPTER).values('subject__title')
    if not relations:
        return None
    return ', '.join(map(lambda obj: '%s' % (obj.get('subject__title')), relations))
