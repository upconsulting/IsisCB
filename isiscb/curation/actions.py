"""
Asynchronous functions for bulk changes to the database.
"""

from __future__ import absolute_import
from curation.tasks import update_instance, bulk_change_tracking_state, bulk_prepend_record_history

from django import forms

from isisdata.models import *
import isisdata.tasks as dtasks
import json
# TODO: refactor these actions to use bulk apply methods and then explicitly
#  trigger search indexing (or whatever other post-save actions are needed).


class BaseAction(object):
    def __init__(self):
        if hasattr(self, 'default_value_field'):
            self.value_field = self.default_value_field
        if hasattr(self, 'default_value_field_kwargs'):
            self.value_field_kwargs = self.default_value_field_kwargs
        if hasattr(self, 'extra'):
            self.extra_fields = self.extra

    def get_value_field(self, **kwargs):
        self.value_field_kwargs.update(kwargs)
        return self.value_field(**self.value_field_kwargs)

    def get_extra_fields(self, **kwargs):
        if hasattr(self, 'extra_fields'):
            return [(name, field(**kwargs)) for name, field, kwargs in self.extra_fields]
        return []


class PrependToRecordHistory(BaseAction):
    model = Citation
    label = u'Update record history'

    default_value_field = forms.CharField
    default_value_field_kwargs = {
        'label': 'Prepend to record history',
        'widget': forms.widgets.Textarea(attrs={'class': 'action-value'}),
    }

    def apply(self, user, filter_params_raw, value, **extra):
        task = AsyncTask.objects.create()
        result = bulk_prepend_record_history.delay(user.id, filter_params_raw,
                                                   value, task.id)

        # We can use the AsyncResult's UUID to access this task later, e.g.
        #  to check the return value or task state.
        task.async_uuid = result.id
        task.value = ('record_status_explanation', value)
        task.save()
        return task.id



class SetRecordStatus(BaseAction):
    model = Citation
    label = u'Set record status'

    default_value_field = forms.ChoiceField
    default_value_field_kwargs = {
        'choices': CuratedMixin.STATUS_CHOICES,
        'label': 'Set record ctatus',
        'widget': forms.widgets.Select(attrs={'class': 'action-value'}),
    }

    def apply(self, user, filter_params_raw, value, **extra):
        # We need this to exist first so that we can keep it up to date as the
        #  group of tasks is executed.

        task = AsyncTask.objects.create()
        result = dtasks.bulk_update_citations.delay(user.id,
                                                    filter_params_raw,
                                                    'record_status_value',
                                                    value, task.id)

        # We can use the AsyncResult's UUID to access this task later, e.g.
        #  to check the return value or task state.
        task.async_uuid = result.id
        task.value = ('record_status_value', value)
        task.save()
        return task.id



class SetRecordStatusExplanation(BaseAction):
    model = Citation
    label = u'Set record status explanation'

    default_value_field = forms.CharField
    default_value_field_kwargs = {
        'label': 'Set record status explanation',
        'widget': forms.widgets.TextInput(attrs={'class': 'action-value'}),
    }

    def apply(self, user, filter_params_raw, value, **extra):
        task = AsyncTask.objects.create()
        result = dtasks.bulk_update_citations.delay(user.id,
                                                    filter_params_raw,
                                                    'record_status_explanation',
                                                    value, task.id)

        # We can use the AsyncResult's UUID to access this task later, e.g.
        #  to check the return value or task state.
        task.async_uuid = result.id
        task.value = ('record_status_explanation', value)
        task.save()
        return task.id


def get_tracking_transition_counts(qs):
    states = zip(*qs.model.TRACKING_CHOICES)[0]
    transitions = dict(zip(states, map(lambda state: qs.filter(tracking_state=state).count(), states)))
    # bugfix for Zotero imports: tracking_state is None not "NO"
    transitions[qs.model.NONE] += qs.filter(tracking_state=None).count()
    return transitions


def get_allowable_transition_states():
    from curation.tracking import TrackingWorkflow
    return dict([(target, source) for source, target in TrackingWorkflow.transitions])


def get_transition_labels():
    from curation.tracking import TrackingWorkflow
    return dict(Tracking.TYPE_CHOICES)


class SetTrackingStatus(BaseAction):
    model = Citation
    label = u'Set record tracking status'

    default_value_field = forms.ChoiceField
    default_value_field_kwargs = {
        'choices': Tracking.TYPE_CHOICES,
        'label': 'Set record tracking status',
        'widget': forms.widgets.Select(attrs={'class': 'action-value'}),
    }

    extra_js = 'curation/js/bulktracking.js'

    extra_fields = (
        ('info', forms.CharField, {'label': 'Tracking Info', 'required': False, 'widget': forms.widgets.TextInput(attrs={'class': 'form-control', 'part_of': 'SetTrackingStatus', 'required': False})}),
        ('notes', forms.CharField, {'label': 'Tracking Notes', 'required': False,  'widget': forms.widgets.Textarea(attrs={'class': 'form-control', 'part_of': 'SetTrackingStatus', 'required': False})}),
    )

    @staticmethod
    def get_extra_data(queryset=None, **kwargs):
        transition_counts = json.dumps(get_tracking_transition_counts(queryset))
        allowable_states = json.dumps(get_allowable_transition_states())
        transition_labels = json.dumps(get_transition_labels())
        return """
        var settrackingstatus_data = {
            transition_counts: %s,
            allowable_states: %s,
            transition_labels: %s
        }""" % (transition_counts, allowable_states, transition_labels)

    def apply(self, user, filter_params_raw, value, info='', notes=''):
        task = AsyncTask.objects.create()
        result = bulk_change_tracking_state.delay(user.id, filter_params_raw, value, info, notes, task.id)

        # We can use the AsyncResult's UUID to access this task later, e.g.
        #  to check the return value or task state.
        task.async_uuid = result.id
        task.value = ('record_status_explanation', value)
        task.save()
        return task.id



AVAILABLE_ACTIONS = [SetRecordStatus, SetRecordStatusExplanation, SetTrackingStatus, PrependToRecordHistory]
