"""
"""

from __future__ import absolute_import, unicode_literals
from __future__ import print_function
from builtins import str
from celery import shared_task
from django.http import QueryDict
from django.db.models import Q
from isisdata.models import Citation, CRUDRule, Authority, AsyncTask, Tenant
from isisdata.filters import CitationFilter, AuthorityFilter
from isisdata.operations import filter_queryset
from django.contrib.auth.models import User
import logging, iso8601
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


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


def _get_filtered_record_queryset(filter_params_raw, user_id=None, type='CITATION'):
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

    if type=='AUTHORITY':
        _qs = Authority.objects.all()
    else:
        _qs = Citation.objects.all()
    if user_id:
        _qs = filter_queryset(User.objects.get(pk=user_id), _qs, CRUDRule.UPDATE)

    if type=='AUTHORITY':
        queryset = AuthorityFilter(filter_params, queryset=_qs).qs
    else:
        queryset = CitationFilter(filter_params, queryset=_qs).qs
    return queryset, filter_params_raw

@shared_task
def save_creation_to_citation(user_id, filter_params_raw, prepend_value, task_id=None, object_type='CITATION'):
    from isisdata.models import AsyncTask

    queryset, _ = _get_filtered_record_queryset(filter_params_raw, user_id, type=object_type)
    task = AsyncTask.objects.get(pk=task_id)
    try:
        for i, obj in enumerate(queryset):
            task.current_value += 1
            task.save()
            created_by = obj.created_by
            # store creator
            if isinstance(created_by, User):
                if object_type == 'AUTHORITY':
                    Authority.objects.filter(pk=obj.id).update(created_by_stored=created_by)
                else:
                    Citation.objects.filter(pk=obj.id).update(created_by_native=created_by)
            # store creation date
            if not obj.created_native:
                if obj.created_on_fm:
                    if object_type == 'AUTHORITY':
                        Authority.objects.filter(pk=obj.id).update(created_on_stored=obj.created_on_fm)
                    else:
                        Citation.objects.filter(pk=obj.id).update(created_native=obj.created_on_fm)
                else:
                    default_date = iso8601.parse_date(settings.CITATION_CREATION_DEFAULT_DATE)
                    if object_type == 'AUTHORITY':
                        Authority.objects.filter(pk=obj.id).update(created_on_stored=default_date)
                    else:
                        Citation.objects.filter(pk=obj.id).update(created_native=default_date)

        task.state = 'SUCCESS'
        task.save()
    except Exception as E:
        logger.exception('save_creator_to_citation failed for %s:: %s' % (filter_params_raw, prepend_value))
        if task_id:
            task = AsyncTask.objects.get(pk=task_id)
            task.value = str(E)
            task.state = 'FAILURE'
            task.save()

@shared_task
def bulk_prepend_record_history(user_id, filter_params_raw, prepend_value, task_id=None, object_type='CITATION'):
    from django.db.models import CharField, Value as V
    from django.db.models.functions import Concat
    from isisdata.models import AsyncTask
    import math, datetime

    user = User.objects.get(pk=user_id)
    now = datetime.datetime.now().strftime('%Y-%m-%d at %I:%M%p')
    prepend_value = 'On %s, %s wrote: %s\n\n' % (now, user.username, prepend_value)

    queryset, _ = _get_filtered_record_queryset(filter_params_raw, user_id, type=object_type)
    queryset.update(record_history=Concat(V(prepend_value), 'record_history'), modified_by=user_id, modified_on=timezone.now())

    try:
        if task_id:
            task = AsyncTask.objects.get(pk=task_id)
            task.state = 'SUCCESS'
            task.save()
            print('success:: %s' % str(task_id))
    except Exception as E:
        print('bulk_prepend_record_history failed for %s:: %s' % (filter_params_raw, prepend_value), end=' ')
        print(E)
        if task_id:
            task = AsyncTask.objects.get(pk=task_id)
            task.value = str(E)
            task.state = 'FAILURE'
            task.save()


@shared_task
def bulk_change_tracking_state(user_id, filter_params_raw, target_state, info,
                               notes, task_id=None, object_type='CITATION'):
    from curation.tracking import TrackingWorkflow
    from isisdata.models import AsyncTask, Tracking
    import math

    queryset, _ = _get_filtered_record_queryset(filter_params_raw, user_id, type=object_type)

    # We should have already filtered out ineligible citations, but just in
    #  case....
    allowed_prior = TrackingWorkflow.allowed(target_state)

    # bugfix ISISCB-1008: if None is in prior allowed states, we need to build a different filter
    q = (Q(tracking_state__in=allowed_prior) | Q(tracking_state__isnull=True)) if None in allowed_prior else Q(tracking_state__in=allowed_prior)
    queryset = queryset.filter(q)

    idents = list(queryset.values_list('id', flat=True))
    try:
        if target_state != Citation.HSTM_UPLOAD:
            queryset.update(tracking_state=target_state, modified_by=user_id, modified_on=timezone.now())
        else:
            queryset.update(hstm_uploaded=Citation.IS_HSTM_UPLOADED, modified_by=user_id, modified_on=timezone.now())
        for ident in idents:
            if object_type == 'AUTHORITY':
                AuthorityTracking.objects.create(authority_id=ident,
                                    type_controlled=target_state,
                                    tracking_info=info,
                                    notes=notes,
                                    modified_by_id=user_id)
            else:
                Tracking.objects.create(citation_id=ident,
                                    type_controlled=target_state,
                                    tracking_info=info,
                                    notes=notes,
                                    modified_by_id=user_id)

        if task_id:
            task = AsyncTask.objects.get(pk=task_id)
            task.state = 'SUCCESS'
            task.save()
            print('success:: %s' % str(task_id))
    except Exception as E:
        logger.error('bulk_change_tracking_state failed for %s:: %s' % (filter_params_raw, target_state))
        logger.error(E)
        if task_id:
            task = AsyncTask.objects.get(pk=task_id)
            task.value = str(E)
            task.state = 'FAILURE'
            task.save()

@shared_task
def bulk_change_tenant(user_id, filter_params_raw, tenant_id, task_id=None, object_type='CITATION'):
    queryset, _ = _get_filtered_record_queryset(filter_params_raw, user_id, type=object_type)
    try:
        # update tenant
        if task_id:
            task = AsyncTask.objects.get(pk=task_id)
        tenant = Tenant.objects.filter(pk=tenant_id).first()
        for i, citation in enumerate(queryset):
            if task_id:
                task.current_value += 1
                task.save()

            citation.tenants.add(tenant)
            citation.save()

        if task_id:
            task = AsyncTask.objects.get(pk=task_id)
            task.state = 'SUCCESS'
            task.save()
            print('success:: %s' % str(task_id))
    except Exception as E:
        logger.error('bulk_change_tracking_state failed for %s:: %s' % (filter_params_raw, target_state))
        logger.error(E)
        if task_id:
            task = AsyncTask.objects.get(pk=task_id)
            task.value = str(E)
            task.state = 'FAILURE'
            task.save()
