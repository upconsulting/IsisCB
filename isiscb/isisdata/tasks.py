from __future__ import absolute_import, unicode_literals
from celery import shared_task

from django.http import QueryDict

from isisdata.filters import CitationFilter, AuthorityFilter
from isisdata.operations import filter_queryset
from isisdata import export    # Oh man, so good.
from isisdata import export_authority
from isisdata.models import *

import unicodecsv as csv
import math, smart_open


def _get_filtered_object_queryset(filter_params_raw, user_id=None, object_type='CITATION'):
    """

    Parameters
    ----------
    params : str

    Returns
    -------
    :class:`.QuerySet`
    """

    # We need a mutable QueryDict.
    filter_params = QueryDict(filter_params_raw, mutable=True)

    if object_type == 'AUTHORITY':
        _qs = Authority.objects.all()
    else:
        _qs = Citation.objects.all()
    if user_id:
        _qs = filter_queryset(User.objects.get(pk=user_id), _qs, CRUDRule.UPDATE)

    if object_type == 'AUTHORITY':
        queryset = AuthorityFilter(filter_params, queryset=_qs).qs
    else:
        queryset = CitationFilter(filter_params, queryset=_qs).qs
    return queryset, filter_params_raw

def _get_filtered_authority_queryset(filter_params_raw, user_id=None):
    """

    Parameters
    ----------
    params : str

    Returns
    -------
    :class:`.QuerySet`
    """

    # We need a mutable QueryDict.
    filter_params = QueryDict(filter_params_raw, mutable=True)

    _qs = Authority.objects.all()
    if user_id:
        _qs = filter_queryset(User.objects.get(pk=user_id), _qs, CRUDRule.UPDATE)
    queryset = AuthorityFilter(filter_params, queryset=_qs).qs
    return queryset, filter_params_raw


@shared_task
def bulk_update_citations(user_id, filter_params_raw, field, value, task_id=None, object_type='CITATION'):
    queryset, _ = _get_filtered_object_queryset(filter_params_raw, user_id, object_type)
    if task_id:
        task = AsyncTask.objects.get(pk=task_id)
        task.max_value = queryset.count()
        _inc = max(2, math.floor(task.max_value / 200.))
        task.save()
    else:
        task = None
    try:    # Report all exceptions as a task failure.
        for i, obj in enumerate(queryset):
            if task and (i % _inc == 0 or i == (task.max_value - 1)):
                task.current_value = i
                task.save()
            setattr(obj, field, value)
            obj.modified_by_id = user_id
            obj.save()
        task.state = 'SUCCESS'
        task.save()
    except Exception as E:
        print 'bulk_update_citations failed for %s' % filter_params_raw,
        print ':: %s:%s' % (field, value),
        print E
        task.state = 'FAILURE'
        task.save()


@shared_task
def export_to_csv(user_id, path, fields, filter_params_raw, task_id=None, export_type='Citation', export_extra=True, config={}):
    print 'export to csv:: %s' % str(task_id)
    if config['export_metadata']:
        fields.append('creator')
        fields.append('modifier')
        fields.append('staff-notes')
        fields.append('record-history')
        fields.append('modified-date')
        fields.append('created-date')
    if export_type == 'Citation':
        queryset, _ = _get_filtered_object_queryset(filter_params_raw, user_id)
        columns = filter(lambda o: o.slug in fields, export.CITATION_COLUMNS)
    else:
        queryset, _ = _get_filtered_authority_queryset(filter_params_raw, user_id)
        columns = filter(lambda o: o.slug in fields, export_authority.AUTHORITY_COLUMNS)
    if task_id:
        task = AsyncTask.objects.get(pk=task_id)
        task.max_value = queryset.count()
        _inc = max(2, math.floor(task.max_value / 200.))
        task.save()
    else:
        task = None

    try:    # Report all exceptions as a task failure.
        with smart_open.smart_open(path, 'wb') as f:
            writer = csv.writer(f)

            writer.writerow(map(lambda c: c.label, columns))
            extra = []
            for i, obj in enumerate(queryset):
                if task and (i % _inc == 0 or i == (task.max_value - 1)):
                    task.current_value = i
                    task.save()
                if obj:
                    writer.writerow(map(lambda c: c(obj, extra, config), columns))

            if export_extra:
                for obj in extra:
                    if obj:
                        writer.writerow(map(lambda c: c(obj, [], config), columns))

        task.state = 'SUCCESS'
        task.save()
        print 'success:: %s' % str(task_id)
    except Exception as E:
        print 'export_to_csv failed for %s' % filter_params_raw,
        print E
        task.value = str(E)
        task.state = 'FAILURE'
        task.save()

@shared_task
def create_timeline(authority_id, timeline_id):
    now = datetime.datetime.now()

    acrelations = ACRelation.objects.all().filter(
        authority__id=authority_id, public=True, citation__public=True,
        citation__attributes__type_controlled__name="PublicationDate").order_by('-citation__publication_date')

    SHOWN_TITLES_COUNT = 3

    counted_citations = []
    timeline_cache = CachedTimeline.objects.get(pk=timeline_id)
    cached_years = {}
    for acrel in acrelations:
        if acrel.citation.id in counted_citations:
            continue

        counted_citations.append(acrel.citation.id)
        year = acrel.citation.publication_date.year

        if not cached_years.get(year, None):
            cached_year = CachedTimelineYear()
            cached_year.year = year
            cached_year.timeline_year = timeline_cache
            cached_year.book_count = 0
            cached_year.thesis_count = 0
            cached_year.chapter_count = 0
            cached_year.article_count = 0
            cached_year.review_count = 0
            cached_year.other_count = 0
            cached_years[year] = cached_year
            cached_year.save()

        title = acrel.citation.title_for_display if acrel.citation.type_controlled in [Citation.REVIEW, Citation.ESSAY_REVIEW] else acrel.citation.title
        if cached_year.titles.all().count() <= SHOWN_TITLES_COUNT:
            cached_title = CachedTimelineTitle()
            cached_title.title = title
            cached_title.citation = acrel.citation
            cached_title.timeline_year = cached_year
            cached_title.citation_type = acrel.citation.type_controlled
            cached_title.save()

        if acrel.citation.type_controlled == Citation.BOOK:
            cached_year.book_count += 1
        elif acrel.citation.type_controlled == Citation.THESIS:
            cached_year.thesis_count += 1
        elif acrel.citation.type_controlled == Citation.CHAPTER:
            cached_year.chapter_count += 1
        elif acrel.citation.type_controlled == Citation.ARTICLE:
            cached_year.article_count += 1
        elif acrel.citation.type_controlled in [Citation.REVIEW, Citation.ESSAY_REVIEW]:
            cached_year.review_count += 1
        else:
            cached_year.other_count += 1
        cached_year.save()
        timeline_cache.save()

    timeline_cache.complete = True
    timeline_cache.save()
