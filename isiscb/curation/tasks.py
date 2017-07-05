"""
"""

from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.http import QueryDict
from django.db.models import Q
from isisdata.models import Citation, CRUDRule
from isisdata.filters import CitationFilter
from isisdata.operations import filter_queryset
from django.contrib.auth.models import User


def _load_model_instance(module, cname, pk, qs=False):
    _mod = __import__(module, fromlist=[cname])
    model = getattr(_mod, cname)
    if qs:
        return model.objects.filter(pk=pk)
    return model.objects.get(pk=pk)


@shared_task
def update_instance(*args, **kwargs):
    if len(args) == 5:    # Called directly with intended signature.
        module, cname, pk, field, value = args
    elif len(args) == 6:    # Upstream task may have returned a value.
        _, module, cname, pk, field, value = args
    obj = _load_model_instance(module, cname, pk)
    setattr(obj, field, value)
    obj.save()


@shared_task
def update_task(task, amount):
    task.current_value += amount
    task.save()


@shared_task
def update_task_status(task, status):
    # task.value = value
    task.status = status
    task.save()


@shared_task
def bulk_update_instances(task_data, queryset, field, value):
    """
    Iteratively update objects in a queryset, using the ``save()`` method.

    This is necessary for some cases in which we need to trigger post-save
    signals and execute instance-specific code.
    """
    task_module, task_model, task_pk = task_data
    task = _load_model_instance(task_module, task_model, task_pk)

    for obj in queryset:
        setattr(obj, field, value)
        obj.save()


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
def bulk_prepend_record_history(user_id, filter_params_raw, prepend_value, task_id=None):
    from django.db.models import CharField, Value as V
    from django.db.models.functions import Concat
    from isisdata.models import AsyncTask
    import math, datetime

    user = User.objects.get(pk=user_id)
    now = datetime.datetime.now().strftime('%Y-%m-%d at %I:%M%p')
    prepend_value = 'On %s, %s wrote: %s\n\n' % (now, user.username, prepend_value)

    queryset, _ = _get_filtered_citation_queryset(filter_params_raw, user_id)
    queryset.update(record_history=Concat(V(prepend_value), 'record_history'))

    try:
        if task_id:
            task = AsyncTask.objects.get(pk=task_id)
            task.state = 'SUCCESS'
            task.save()
            print 'success:: %s' % str(task_id)
    except Exception as E:
        print 'bulk_prepend_record_history failed for %s:: %s' % (filter_params_raw, prepend_value),
        print E
        if task_id:
            task = AsyncTask.objects.get(pk=task_id)
            task.value = str(E)
            task.state = 'FAILURE'
            task.save()


@shared_task
def bulk_change_tracking_state(user_id, filter_params_raw, target_state, info,
                               notes, task_id=None):
    from curation.tracking import TrackingWorkflow
    from isisdata.models import AsyncTask, Tracking
    import math

    queryset, _ = _get_filtered_citation_queryset(filter_params_raw, user_id)

    # We should have already filtered out ineligible citations, but just in
    #  case....
    allowed_prior = TrackingWorkflow.allowed(target_state)

    # bugfix ISISCB-1008: if None is in prior allowed states, we need to build a different filter
    q = (Q(tracking_state__in=allowed_prior) | Q(tracking_state__isnull=True)) if None in allowed_prior else Q(tracking_state__in=allowed_prior)
    queryset = queryset.filter(q)
    
    idents = list(queryset.values_list('id', flat=True))
    try:
        queryset.update(tracking_state=target_state)
        for ident in idents:
            Tracking.objects.create(citation_id=ident,
                                    type_controlled=target_state,
                                    tracking_info=info,
                                    notes=notes,
                                    modified_by_id=user_id)

        if task_id:
            task = AsyncTask.objects.get(pk=task_id)
            task.state = 'SUCCESS'
            task.save()
            print 'success:: %s' % str(task_id)
    except Exception as E:
        print 'bulk_change_tracking_state failed for %s:: %s' % (filter_params_raw, target_state),
        print E
        if task_id:
            task = AsyncTask.objects.get(pk=task_id)
            task.value = str(E)
            task.state = 'FAILURE'
            task.save()
