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
        # we need to call the save method rather than a queryset update
        # otherwise post hooks are not being called since the update
        # is executed directly on the database
        for record in queryset.all():
            record.record_status_value=value
            record.save()


class SetRecordStatusExplanation(BaseAction):
    model = Citation
    label = u'Set record status explanation'

    default_value_field = forms.CharField
    default_value_field_kwargs = {
        'label': 'Set record status explanation',
        'widget': forms.widgets.TextInput(attrs={'class': 'action-value'}),
    }

    def apply(self, queryset, value):
        # we need to call the save method rather than a queryset update
        # otherwise post hooks are not being called since the update
        # is executed directly on the database
        for record in queryset.all():
            record.record_status_explanation=value
            record.save()


AVAILABLE_ACTIONS = [SetRecordStatus, SetRecordStatusExplanation]
