"""
"""

from __future__ import absolute_import, unicode_literals
from celery import shared_task


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
