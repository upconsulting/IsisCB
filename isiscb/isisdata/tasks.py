from __future__ import absolute_import, unicode_literals
from celery import shared_task

from django.http import QueryDict

from isisdata.filters import CitationFilter
from isisdata.operations import filter_queryset
from isisdata import export    # Oh man, so good.
from isisdata.models import *

import unicodecsv as csv
import math, smart_open


def _get_filtered_citation_queryset(filter_params_raw, user_id=None):
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

    _qs = Citation.objects.all()
    if user_id:
        _qs = filter_queryset(User.objects.get(pk=user_id), _qs, CRUDRule.UPDATE)
    queryset = CitationFilter(filter_params, queryset=_qs).qs
    return queryset, filter_params_raw


@shared_task
def bulk_update_citations(user_id, filter_params_raw, field, value, task_id=None):
    queryset, _ = _get_filtered_citation_queryset(filter_params_raw, user_id)
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
def export_to_csv(user_id, path, fields, filter_params_raw, task_id=None):
    columns = filter(lambda o: o.slug in fields, export.CITATION_COLUMNS)
    queryset, _ = _get_filtered_citation_queryset(filter_params_raw, user_id)
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
            for i, obj in enumerate(queryset):
                if task and (i % _inc == 0 or i == (task.max_value - 1)):
                    task.current_value = i
                    task.save()
                writer.writerow(map(lambda c: c(obj), columns))
        task.state = 'SUCCESS'
        task.save()
    except Exception as E:
        print 'export_to_csv failed for %s' % filter_params_raw,
        print E
        task.state = 'FAILURE'
        task.save()
