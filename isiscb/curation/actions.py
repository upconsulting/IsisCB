from __future__ import absolute_import

from django import forms

from isisdata.models import *


class BaseAction(object):
    def __init__(self):
        if hasattr(self, 'default_value_field'):
            self.value_field = self.default_value_field
        if hasattr(self, 'default_value_field_kwargs'):
            self.value_field_kwargs = self.default_value_field_kwargs

    def get_value_field(self, **kwargs):
        self.value_field_kwargs.update(kwargs)
        return self.value_field(**self.value_field_kwargs)


class SetRecordStatus(BaseAction):
    model = Citation
    label = u'Set record status'

    default_value_field = forms.ChoiceField
    default_value_field_kwargs = {
        'choices': CuratedMixin.STATUS_CHOICES,
        'label': 'Set record ctatus',
        'widget': forms.widgets.Select(attrs={'class': 'action-value'}),
    }

    def apply(self, queryset, value):
        queryset.update(record_status_value=value)
        queryset.update(public=(value=='Active'))


class SetRecordStatusExplanation(BaseAction):
    model = Citation
    label = u'Set record status explanation'

    default_value_field = forms.CharField
    default_value_field_kwargs = {
        'label': 'Set record status explanation',
        'widget': forms.widgets.TextInput(attrs={'class': 'action-value'}),
    }

    def apply(self, queryset, value):
        queryset.update(record_status_explanation=value)


AVAILABLE_ACTIONS = [SetRecordStatus, SetRecordStatusExplanation]
