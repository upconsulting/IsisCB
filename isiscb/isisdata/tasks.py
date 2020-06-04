from __future__ import absolute_import, unicode_literals
from __future__ import print_function
from __future__ import division
from builtins import str
from past.utils import old_div
from celery import shared_task

from django.http import QueryDict

from isisdata.filters import CitationFilter, AuthorityFilter
from isisdata.operations import filter_queryset
from isisdata import export, export_ebsco, export_item_count_csv, export_swp_analysis_csv    # Oh man, so good.
from isisdata import export_authority
from isisdata.models import *

from django.conf import settings

import csv
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
        _inc = max(2, math.floor(old_div(task.max_value, 200.)))
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
        print('bulk_update_citations failed for %s' % filter_params_raw, end=' ')
        print(':: %s:%s' % (field, value), end=' ')
        print(E)
        task.state = 'FAILURE'
        task.save()


@shared_task
def export_to_csv(user_id, path, fields, filter_params_raw, task_id=None, export_type='Citation', export_extra=True, config={}):
    print('export to csv:: %s' % str(task_id))
    if config['export_metadata']:
        fields.append('creator')
        fields.append('modifier')
        fields.append('staff-notes')
        fields.append('record-history')
        fields.append('modified-date')
        fields.append('created-date')
    if export_type == 'Citation':
        queryset, _ = _get_filtered_object_queryset(filter_params_raw, user_id)
        columns = [o for o in export.CITATION_COLUMNS if o.slug in fields]
    else:
        queryset, _ = _get_filtered_authority_queryset(filter_params_raw, user_id)
        columns = [o for o in export_authority.AUTHORITY_COLUMNS if o.slug in fields]
    if task_id:
        task = AsyncTask.objects.get(pk=task_id)
        task.max_value = queryset.count()
        _inc = max(2, math.floor(old_div(task.max_value, 200.)))
        task.save()
    else:
        task = None

    try:    # Report all exceptions as a task failure.
        with smart_open.smart_open(path, 'wb') as f:
            writer = csv.writer(f)

            writer.writerow([c.label for c in columns])
            extra = []
            for i, obj in enumerate(queryset):
                if task and (i % _inc == 0 or i == (task.max_value - 1)):
                    task.current_value = i
                    task.save()
                if obj:
                    writer.writerow([c(obj, extra, config) for c in columns])

            if export_extra:
                for obj in extra:
                    if obj:
                        writer.writerow([c(obj, [], config) for c in columns])

        task.state = 'SUCCESS'
        task.save()
        print('success:: %s' % str(task_id))
    except Exception as E:
        print('export_to_csv failed for %s' % filter_params_raw, end=' ')
        print(E)
        task.value = str(E)
        task.state = 'FAILURE'
        task.save()

@shared_task
def export_to_ebsco_csv(user_id, path, fields, filter_params_raw, task_id=None, export_type='Citation', export_extra=True, config={}):
    print('export to EBSCO csv:: %s' % str(task_id))
    if export_type == 'Citation':
        queryset, _ = _get_filtered_object_queryset(filter_params_raw, user_id)
        columns = export_ebsco.CITATION_COLUMNS
    else:
        print("Exporting authorities not supported in EBSCO format.")
        return

    _generate_csv(columns, task_id, queryset, path, filter_params_raw, config, export_extra)

@shared_task
def export_item_counts(user_id, path, fields, filter_params_raw, task_id=None, export_type='Citation', export_extra=True, config={}):
    print('export item counts csv:: %s' % str(task_id))
    if export_type == 'Citation':
        queryset, _ = _get_filtered_object_queryset(filter_params_raw, user_id)
        columns = export_item_count_csv.CITATION_COLUMNS
    else:
        print("Exporting authorities not supported for item count.")
        return

    _generate_csv(columns, task_id, queryset, path, filter_params_raw, config, export_extra)

@shared_task
def export_swp_analysis(user_id, path, fields, filter_params_raw, task_id=None, export_type='Citation', export_extra=True, config={}):
    print('export item counts csv:: %s' % str(task_id))
    if export_type == 'Citation':
        queryset, _ = _get_filtered_object_queryset(filter_params_raw, user_id)
        columns = export_swp_analysis_csv.CITATION_COLUMNS
    else:
        print("Exporting authorities not supported for item count.")
        return

    _generate_csv(columns, task_id, queryset, path, filter_params_raw, config, export_extra)

def _generate_csv(columns, task_id, queryset, path, filter_params_raw, config, export_extra):
    if task_id:
        task = AsyncTask.objects.get(pk=task_id)
        task.max_value = queryset.count()
        _inc = max(2, math.floor(old_div(task.max_value, 200.)))
        task.save()
    else:
        task = None

    try:    # Report all exceptions as a task failure.
        with smart_open.smart_open(path, 'wb') as f:
            writer = csv.writer(f)

            writer.writerow([c.label for c in columns])
            extra = []
            for i, obj in enumerate(queryset):
                if task and (i % _inc == 0 or i == (task.max_value - 1)):
                    task.current_value = i
                    task.save()
                if obj:
                    writer.writerow([c(obj, extra, config) for c in columns])

            if export_extra:
                for obj in extra:
                    if obj:
                        writer.writerow([c(obj, [], config) for c in columns])

        task.state = 'SUCCESS'
        task.save()
        print('success:: %s' % str(task_id))
    except Exception as E:
        print('export_to_csv failed for %s' % filter_params_raw, end=' ')
        print(E)
        task.value = str(E)
        task.state = 'FAILURE'
        task.save()

@shared_task
def create_timeline(authority_id, timeline_id):
    now = datetime.datetime.now()

    acrelations = ACRelation.objects.all().filter(
        authority__id=authority_id, public=True, citation__public=True,
        citation__attributes__type_controlled__name=settings.TIMELINE_PUBLICATION_DATE_ATTRIBUTE).order_by('-citation__publication_date')

    SHOWN_TITLES_COUNT = 3

    counted_citations = []
    timeline_cache = CachedTimeline.objects.get(pk=timeline_id)
    cached_years = {}
    for acrel in acrelations:
        if acrel.citation.id in counted_citations or not acrel.citation.publication_date:
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
        if cached_year.titles.filter(citation_type=acrel.citation.type_controlled).count() < SHOWN_TITLES_COUNT:
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

    # delete previous timelines
    cached_timelines = CachedTimeline.objects.filter(authority_id=authority_id).exclude(pk=timeline_id).delete()
