from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from past.utils import old_div
from celery import shared_task
from django.conf import settings

from isisdata.models import *
from isisdata.tasks import _get_filtered_object_queryset
import haystack

import math

@shared_task
def reindex_citations(user_id, filter_params_raw, task_id=None, object_type='CITATION'):

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

            haystack.connections[settings.HAYSTACK_DEFAULT_INDEX].get_unified_index().get_index(Citation).update_object(obj)

        task.state = 'SUCCESS'
        task.save()
    except Exception as E:
        print('bulk_update_citations failed for %s' % filter_params_raw, end=' ')
        print(E)
        task.state = 'FAILURE'
        task.save()
