from __future__ import absolute_import
from __future__ import unicode_literals

from builtins import str
from builtins import object
from django import forms
from django.http import QueryDict

from isisdata.models import *
from isisdata import export    # This never gets old...
from isisdata import export_authority
from curation import actions

import rules


class CCRelationForm(forms.ModelForm):
    subject = forms.CharField(widget=forms.HiddenInput(), required=True)
    object = forms.CharField(widget=forms.HiddenInput(), required=True)
    """We will set these dynamically in the rendered form."""

    record_status_value = forms.ChoiceField(choices=CuratedMixin.STATUS_CHOICES, required=False)

    INCLUDES_CHAPTER = 'IC'
    INCLUDES_SERIES_ARTICLE = 'ISA'
    INCLUDES_CITATION_OBJECT = "ICO"
    REVIEWED_BY = 'RB'
    RESPONDS_TO = 'RE'
    ASSOCIATED_WITH = 'AS'
    TYPE_CHOICES = (
        (INCLUDES_CHAPTER, 'Includes Chapter'),
        (INCLUDES_SERIES_ARTICLE, 'Includes Series Article'),
        (INCLUDES_CITATION_OBJECT, 'Includes'),
        (ASSOCIATED_WITH, 'Is Associated With'),
        (REVIEWED_BY, 'Is Reviewed By')
    )
    type_controlled = forms.ChoiceField(choices=TYPE_CHOICES)

    def __init__(self, *args, **kwargs):
        super(CCRelationForm, self).__init__(*args, **kwargs)
        if not self.is_bound:
            if not self.fields['record_status_value'].initial:
                self.fields['record_status_value'].initial = CuratedMixin.ACTIVE

    def clean(self):
        super(CCRelationForm, self).clean()
        subject_id = self.cleaned_data.get('subject', None)
        if subject_id:
            self.cleaned_data['subject'] = Citation.objects.get(pk=subject_id)

        object_id = self.cleaned_data.get('object', None)
        if object_id:
            self.cleaned_data['object'] = Citation.objects.get(pk=object_id)

    class Meta:
        model = CCRelation
        fields = [
            'type_controlled', 'data_display_order', 'subject',
            'object', 'record_status_value', 'record_status_explanation',
            'administrator_notes', 'record_history',
        ]
        labels = {
            'administrator_notes': 'Staff notes'
        }



class ACRelationForm(forms.ModelForm):
    authority = forms.CharField(widget=forms.HiddenInput(), required=False)
    citation = forms.CharField(widget=forms.HiddenInput(), required=False)
    """We will set these dynamically in the rendered form."""

    record_status_value = forms.ChoiceField(choices=CuratedMixin.STATUS_CHOICES, required=False)

    type_controlled = forms.ChoiceField(choices=ACRelation.TYPE_CHOICES, required=False)

    confidence_measure = forms.TypedChoiceField(**{
        'choices': [
            (1.0, 'Certain/very likely'),
            (0.5, 'Likely'),
            (0.0, 'Unsure'),
        ],
        'coerce': float,
        'required': True,
    })

    class Meta(object):
        model = ACRelation
        fields = [
            'type_controlled',
            'name_for_display_in_citation', 'data_display_order',
            'confidence_measure', 'authority', 'citation',
            'record_status_value', 'record_status_explanation',
            'administrator_notes', 'record_history'
        ]
        labels = {
            'administrator_notes': 'Staff notes',
        }

    def __init__(self, *args, **kwargs):
        super(ACRelationForm, self).__init__(*args, **kwargs)
        if not self.is_bound:
            if not self.fields['record_status_value'].initial:
                self.fields['record_status_value'].initial = CuratedMixin.ACTIVE

    def clean(self):
        super(ACRelationForm, self).clean()
        authority_id = self.cleaned_data.get('authority', None)
        if authority_id:
            self.cleaned_data['authority'] = Authority.objects.get(pk=authority_id)
        else:
            self.cleaned_data['authority'] = None
        citation_id = self.cleaned_data.get('citation', None)
        if citation_id:
            self.cleaned_data['citation'] = Citation.objects.get(pk=citation_id)
        else:
            self.cleaned_data['citation'] = None


class AARelationForm(forms.ModelForm):
    authority_subject = forms.CharField(widget=forms.HiddenInput(), required=False)
    authority_object = forms.CharField(widget=forms.HiddenInput(), required=False)
    """We will set these dynamically in the rendered form."""

    record_status_value = forms.ChoiceField(choices=CuratedMixin.STATUS_CHOICES, required=False)

    type_controlled = forms.ChoiceField(choices=AARelation.TYPE_CHOICES, required=False)

    confidence_measure = forms.TypedChoiceField(**{
        'choices': [
            (1.0, 'Certain/very likely'),
            (0.5, 'Likely'),
            (0.0, 'Unsure'),
        ],
        'coerce': float,
        'required': False,
    })

    class Meta(object):
        model = AARelation
        fields = [
            'type_controlled', 'aar_type',
            'confidence_measure', 'subject', 'object',
            'record_status_value', 'record_status_explanation',
            'administrator_notes', 'record_history'
        ]
        labels = {
            'administrator_notes': 'Staff notes',
        }

    def __init__(self, *args, **kwargs):
        super(AARelationForm, self).__init__(*args, **kwargs)
        self.fields['subject'].required=False
        self.fields['object'].required=False
        if not self.is_bound:
            if not self.fields['record_status_value'].initial:
                self.fields['record_status_value'].initial = CuratedMixin.ACTIVE
            if not self.fields['authority_subject'].initial and self.instance.subject:
                self.fields['authority_subject'].initial = self.instance.subject.id
            if not self.fields['authority_object'].initial and self.instance.object:
                self.fields['authority_object'].initial = self.instance.object.id

    def clean(self):
        super(AARelationForm, self).clean()

        if self.cleaned_data.get('aar_type', None):
            self.cleaned_data['type_controlled'] +  self.cleaned_data.get('aar_type').base_type
        authority_subject_id = self.cleaned_data.get('authority_subject', None)
        if authority_subject_id:
            self.cleaned_data['subject'] = Authority.objects.get(pk=authority_subject_id)
        else:
            self.cleaned_data['subject'] = None
        authority_object_id = self.cleaned_data.get('authority_object', None)
        if authority_object_id:
            self.cleaned_data['object'] = Authority.objects.get(pk=authority_object_id)
        else:
            self.cleaned_data['object'] = None


class ISODateValueForm(forms.ModelForm):
    value = forms.CharField()

    def __init__(self, *args, **kwargs):
        super(ISODateValueForm, self).__init__(*args, **kwargs)
        instance = kwargs.get('instance')

        if instance and not self.is_bound:
            self.fields['value'].initial = instance.__unicode__()

    def clean_value(self):
        value = self.cleaned_data['value']
        try:
            ISODateValue.convert(value)
        except:
            raise forms.ValidationError('Please enter an ISO8601-compliant date.')
        return value

    def save(self, *args, **kwargs):
        self.instance.value = self.cleaned_data.get('value')
        super(ISODateValueForm, self).save(*args, **kwargs)

    class Meta(object):
        model = ISODateValue
        fields = []

class AuthorityValueForm(forms.ModelForm):
    value = forms.CharField(label="Authority ID")
    authority_name = forms.CharField(label='Name of stored authority')

    def __init__(self, *args, **kwargs):
        super(AuthorityValueForm, self).__init__(*args, **kwargs)
        instance = kwargs.get('instance')

        if instance and not self.is_bound:
            self.fields['value'].initial = instance.pk
            self.fields['authority_name'].initial = instance.value.name
            self.fields['authority_name'].widget.attrs['readonly'] = True

    def clean_value(self):
        value = self.cleaned_data['value']

        try:
            value = Authority.objects.get(id=value)
        except:
            raise forms.ValidationError('Authority record does not exist.')

        return value

    def save(self, *args, **kwargs):
        self.instance.value = self.cleaned_data.get('value')
        super(AuthorityValueForm, self).save(*args, **kwargs)

    class Meta(object):
        model = AuthorityValue
        fields = ['value']

class CitationValueForm(forms.ModelForm):
    value = forms.CharField(label="Citation ID", widget=forms.TextInput(attrs={'data-type':'citation_id'}))
    citation_name = forms.CharField(label='Name of stored citation', widget=forms.TextInput(attrs={'readonly': True}))

    def __init__(self, *args, **kwargs):
        super(CitationValueForm, self).__init__(*args, **kwargs)
        instance = kwargs.get('instance')

        if instance and not self.is_bound:
            self.fields['value'].initial = instance.pk
            self.fields['citation_name'].initial = instance.value.title_for_display
            
    def clean_value(self):
        value = self.cleaned_data['value']

        try:
            value = Citation.objects.get(id=value)
        except:
            raise forms.ValidationError('Citation record does not exist.')

        return value

    def save(self, *args, **kwargs):
        self.instance.value = self.cleaned_data.get('value')
        super(CitationValueForm, self).save(*args, **kwargs)

    class Meta(object):
        model = CitationValue
        fields = ['value']

class PartDetailsForm(forms.ModelForm):
    extent_note = forms.CharField(widget=forms.widgets.Textarea({'rows': '1'}), required=False)

    def __init__(self, user, citation_id=None, *args, **kwargs):
        super(PartDetailsForm, self).__init__( *args, **kwargs)
        self.user = user
        self.citation_id = citation_id

        self.fields['volume_begin'].widget.attrs['placeholder'] = "Begin #"
        self.fields['volume_end'].widget.attrs['placeholder'] = "End #"
        self.fields['volume_free_text'].widget.attrs['placeholder'] = "Volume"
        self.fields['issue_begin'].widget.attrs['placeholder'] = "Begin #"
        self.fields['issue_end'].widget.attrs['placeholder'] = "End #"
        self.fields['issue_free_text'].widget.attrs['placeholder'] = "Issue"
        self.fields['page_begin'].widget.attrs['placeholder'] = "Begin #"
        self.fields['page_end'].widget.attrs['placeholder'] = "End #"
        self.fields['pages_free_text'].widget.attrs['placeholder'] = "Pages"
        self.fields['extent'].widget.attrs['placeholder'] = "Extent"
        self.fields['extent_note'].widget.attrs['placeholder'] = "Extent note"


        if citation_id:
            can_update = rules.test_rule('can_update_citation_field', user, ('part_details', citation_id))
            can_view = rules.test_rule('can_view_citation_field', user, ('part_details', citation_id))

            set_field_access(can_update, can_view, self.fields)

    class Meta(object):
        model = PartDetails
        exclude =['volume', 'sort_order']

    def _get_validation_exclusions(self):
        exclude = super(PartDetailsForm, self)._get_validation_exclusions()

        # remove fields that user isn't allowed to modify
        if self.citation_id:
            can_update = rules.test_rule('can_update_citation_field', self.user, ('part_details', self.citation_id))
            can_view = rules.test_rule('can_view_citation_field', self.user, ('part_details', self.citation_id))

            for field in self.fields:
                if not can_update or not can_view:
                    exclude.append(field)

        return exclude


def set_field_access(can_update, can_view, fields):
    for field in fields:
        if not can_update:
            fields[field].widget.attrs['readonly'] = True

        if not can_view:
            fields[field] = forms.CharField(widget=NoViewInput())
            fields[field].widget.attrs['readonly'] = True

class StubCheckboxInput(forms.widgets.CheckboxInput):

    def __init__(self, attrs=None, check_test=None):
        super().__init__(attrs, lambda v: v == Citation.STUB_RECORD)

class CitationForm(forms.ModelForm):

    abstract = forms.CharField(widget=forms.widgets.Textarea({'rows': '7'}), required=False)
    complete_citation = forms.CharField(widget=forms.widgets.Textarea({'rows': '7'}), required=False)
    description = forms.CharField(widget=forms.widgets.Textarea({'rows': '3'}), required=False)
    record_history = forms.CharField(widget=forms.widgets.Textarea({'rows': '3'}), required=False)

    additional_titles = forms.CharField(widget=forms.widgets.Textarea({'rows': '2'}), required=False)
    edition_details = forms.CharField(widget=forms.widgets.Textarea({'rows': '2'}), required=False)
    physical_details = forms.CharField(widget=forms.widgets.Textarea({'rows': '2'}), required=False)

    language = forms.ModelMultipleChoiceField(queryset=Language.objects.all(), required=False)

    belongs_to = forms.ModelChoiceField(queryset=Dataset.objects.all(), label='Dataset', required=False)
    record_status_value = forms.ChoiceField(choices=CuratedMixin.STATUS_CHOICES, required=False)

    administrator_notes = forms.CharField(widget=forms.widgets.Textarea({'rows': '3'}), required=False, label="Staff notes")
    title = forms.CharField(widget=forms.widgets.Textarea({'rows': '3'}), required=False)

    subtype = forms.ModelChoiceField(queryset=CitationSubtype.objects.all(), label='Subtype', required=False)
    stub_record_status = forms.BooleanField(label='Stub', widget=StubCheckboxInput(), required=False)

    class Meta(object):
        model = Citation
        fields = [
            'type_controlled', 'title', 'description', 'edition_details',
              'physical_details', 'abstract', 'additional_titles',
              'book_series', 'record_status_value', 'record_status_explanation',
              'belongs_to', 'administrator_notes', 'record_history', 'subtype',
              'complete_citation', 'stub_record_status'
        ]
        labels = {
            'belongs_to': 'Dataset',
            'administrator_notes': 'Staff notes',
            'complete_citation': 'Stub text'
        }

    def __init__(self, user, *args, **kwargs):
        super(CitationForm, self).__init__( *args, **kwargs)
        self.user = user

        if not self.is_bound:
            if not self.fields['record_status_value'].initial:
                self.fields['record_status_value'].initial = CuratedMixin.ACTIVE

        # disable fields user doesn't have access to
        if self.instance.pk:
            self.fields['title'].widget.attrs['placeholder'] = "No title"
            self.fields['type_controlled'].widget = forms.widgets.HiddenInput()

            if self.instance.type_controlled in [Citation.REVIEW, Citation.CHAPTER, Citation.ARTICLE, Citation.ESSAY_REVIEW]:
                self.fields['book_series'].widget = forms.widgets.HiddenInput()

            if self.instance.type_controlled in [Citation.THESIS]:
                self.fields['book_series'].widget = forms.widgets.HiddenInput()

            self.fields['subtype'].queryset = CitationSubtype.objects.filter(related_citation_type=self.instance.type_controlled)

            for field in self.fields:
                can_update = rules.test_rule('can_update_citation_field', user, (field, self.instance.pk))
                if not can_update:
                    self.fields[field].widget.attrs['readonly'] = True
                    self.fields[field].widget.attrs['disabled'] = True


                can_view = rules.test_rule('can_view_citation_field', user, (field, self.instance.pk))
                if not can_view:
                    self.fields[field] = forms.CharField(widget=NoViewInput())
                    self.fields[field].widget.attrs['readonly'] = True
                    self.fields[field].widget.attrs['disabled'] = True

    def clean(self):
        super(CitationForm, self).clean()

        stub_record_status = self.cleaned_data.get('stub_record_status', False)
        if stub_record_status:
            self.cleaned_data['stub_record_status'] = Citation.STUB_RECORD
        else:
            self.cleaned_data['stub_record_status'] = None

    def _get_validation_exclusions(self):
        exclude = super(CitationForm, self)._get_validation_exclusions()

        # remove fields that user isn't allowed to modify
        if self.instance.pk:
            for field in self.fields:
                can_update = rules.test_rule('can_update_citation_field', self.user, (field, self.instance.pk))
                can_view = rules.test_rule('can_view_citation_field', self.user, (field, self.instance.pk))
                if not can_update or not can_view:
                    exclude.append(field)
        return exclude


class LinkedDataForm(forms.ModelForm):

    class Meta(object):
        model = LinkedData
        fields = [
            'universal_resource_name', 'resource_name', 'url',
            'type_controlled', 'record_status_value',
            'record_status_explanation', 'administrator_notes',
            'record_history'
        ]
        labels = {
            'universal_resource_name': 'URN (link to authority)'
        }

    def __init__(self, *args, **kwargs):
        super(LinkedDataForm, self).__init__(*args, **kwargs)

        if not self.is_bound:
            if not self.fields['record_status_value'].initial:
                self.fields['record_status_value'].initial = CuratedMixin.ACTIVE

    def save(self, *args, **kwargs):
        super(LinkedDataForm, self).save(*args, **kwargs)


class NoViewInput(forms.TextInput):

    def render(self, name, value, attrs=None):
        value = "You do not have sufficient permissions to view this field."
        return super(NoViewInput, self).render(name, value, attrs)


class AuthorityForm(forms.ModelForm):
    description = forms.CharField(widget=forms.widgets.Textarea({'rows': '3'}), required=False)
    record_status_value = forms.ChoiceField(choices=CuratedMixin.STATUS_CHOICES, required=False)
    redirect_to = forms.CharField(widget=forms.HiddenInput(), required = False)
    record_history = forms.CharField(widget=forms.widgets.Textarea({'rows': '3'}), required=False)
    belongs_to = forms.ModelChoiceField(queryset=Dataset.objects.all(), label='Dataset', required=False)

    class Meta(object):
        model = Authority
        fields = [
            'type_controlled', 'name', 'description', 'classification_system',
            'classification_code', 'classification_hierarchy',
            'record_status_value', 'record_status_explanation', 'redirect_to',
            'administrator_notes', 'record_history', 'belongs_to'
        ]

        labels = {
            'belongs_to': 'Dataset',
            'administrator_notes': 'Staff notes',
        }


    def __init__(self, user, *args, **kwargs):
        super(AuthorityForm, self).__init__(*args, **kwargs)
        if not self.is_bound:
            if not self.fields['record_status_value'].initial:
                self.fields['record_status_value'].initial = CuratedMixin.ACTIVE

        self.user = user

        # disable fields user doesn't have access to
        if self.instance.pk:
            for field in self.fields:
                can_update = rules.test_rule('can_update_authority_field', user, (field, self.instance.pk))
                if not can_update:
                    self.fields[field].widget.attrs['readonly'] = True

                can_view = rules.test_rule('can_view_authority_field', user, (field, self.instance.pk))
                if not can_view:
                    self.fields[field] = forms.CharField(widget=NoViewInput())
                    self.fields[field].widget.attrs['readonly'] = True

    def clean(self):
        super(AuthorityForm, self).clean()
        authority_id = self.cleaned_data['redirect_to']
        if authority_id:
            self.cleaned_data['redirect_to'] = Authority.objects.get(pk=authority_id)
        else:
            self.cleaned_data['redirect_to'] = None

    def _get_validation_exclusions(self):
        exclude = super(AuthorityForm, self)._get_validation_exclusions()

        # remove fields that user isn't allowed to modify
        if self.instance.pk:
            for field in self.fields:
                can_update = rules.test_rule('can_update_authority_field', self.user, (field, self.instance.pk))
                can_view = rules.test_rule('can_view_authority_field', self.user, (field, self.instance.pk))
                if not can_update or not can_view:
                    exclude.append(field)

        return exclude


class CitationTrackingForm(forms.ModelForm):

    HSTM_UPLOAD = 'HS'
    PRINTED = 'PT'
    AUTHORIZED = 'AU'
    PROOFED = 'PD'
    FULLY_ENTERED = 'FU'
    BULK_DATA = 'BD'
    TYPE_CHOICES = (
        (HSTM_UPLOAD, 'HSTM Upload'),
        (PRINTED, 'Printed'),
        (AUTHORIZED, 'Authorized'),
        (PROOFED, 'Proofed'),
        (FULLY_ENTERED, 'Fully Entered'),
        (BULK_DATA, 'Bulk Data Update')
    )

    type_controlled = forms.ChoiceField(required=True,
                                       choices=TYPE_CHOICES)

    class Meta(object):
        model = Tracking
        fields = [
            'tracking_info', 'notes', 'type_controlled'
        ]


class AuthorityTrackingForm(forms.ModelForm):

    HSTM_UPLOAD = 'HS'
    PRINTED = 'PT'
    AUTHORIZED = 'AU'
    PROOFED = 'PD'
    FULLY_ENTERED = 'FU'
    BULK_DATA = 'BD'
    TYPE_CHOICES = (
        (HSTM_UPLOAD, 'HSTM Upload'),
        (PRINTED, 'Printed'),
        (AUTHORIZED, 'Authorized'),
        (PROOFED, 'Proofed'),
        (FULLY_ENTERED, 'Fully Entered'),
        (BULK_DATA, 'Bulk Data Update')
    )

    type_controlled = forms.ChoiceField(required=True,
                                       choices=TYPE_CHOICES)

    class Meta(object):
        model = AuthorityTracking
        fields = [
            'tracking_info', 'notes', 'type_controlled'
        ]


class PersonForm(forms.ModelForm):
    description = forms.CharField(widget=forms.widgets.Textarea({'rows': '3'}), required=False)

    def __init__(self, user, authority_id, *args, **kwargs):
        super(PersonForm, self).__init__( *args, **kwargs)
        self.user = user
        self.authority_id = authority_id

        if authority_id:
            can_update = rules.test_rule('can_update_authority_field', user, ('person', authority_id))
            can_view = rules.test_rule('can_view_authority_field', user, ('person', authority_id))

            set_field_access(can_update, can_view, self.fields)

    class Meta(object):
        model = Person
        fields = [
            'personal_name_last', 'personal_name_first', 'personal_name_suffix',
            'personal_name_preferred',
        ]

    def _get_validation_exclusions(self):
        exclude = super(PersonForm, self)._get_validation_exclusions()

        if self.authority_id:
            # remove fields that user isn't allowed to modify
            can_update = rules.test_rule('can_update_authority_field', self.user, ('person', self.authority_id))
            can_view = rules.test_rule('can_view_authority_field', self.user, ('person', self.authority_id))

            for field in self.fields:
                if not can_update or not can_view:
                    exclude.append(field)

        return exclude


class RoleForm(forms.ModelForm):

    class Meta(object):
        model = IsisCBRole
        fields = [
            'name', 'description',
        ]


class DatasetRuleForm(forms.ModelForm):
    dataset = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super(DatasetRuleForm, self).__init__( *args, **kwargs)

        dataset_values = Dataset.objects.all()
        choices = set()
        choices.add((None, "No Dataset"))
        for ds in dataset_values:
            choices.add((ds.pk, ds.name))
        self.fields['dataset'].choices = choices

    def clean_field(self):
        data = self.cleaned_data['dataset']
        if data == '':
            data = None

        return data

    class Meta(object):
        model = DatasetRule

        fields = [
            'dataset', 'role'
        ]


class AddRoleForm(forms.Form):
    role = forms.ChoiceField(required=True)

    def __init__(self, *args, **kwargs):
        super(AddRoleForm, self).__init__( *args, **kwargs)

        roles = IsisCBRole.objects.all()
        choices = []
        for role in roles:
            choices.append((role.pk, role.name))
        self.fields['role'].choices = choices

class CRUDRuleForm(forms.ModelForm):

    class Meta(object):
        model = CRUDRule
        fields = [
            'crud_action'
        ]
        labels = {
            'crud_action': 'Allowed Action',
        }

class FieldRuleCitationForm(forms.ModelForm):

    field_name = forms.ChoiceField(required = True)

    def __init__(self, *args, **kwargs):
        super(FieldRuleCitationForm, self).__init__( *args, **kwargs)

        all_citation_fields = Citation._meta.get_fields()
        choices = []
        for field in all_citation_fields:
            choices.append((field.name, field.name))
        choices.sort()
        self.fields['field_name'].choices = choices


    class Meta(object):
        model = FieldRule
        fields = [
            'field_action', 'field_name',
        ]

class FieldRuleAuthorityForm(forms.ModelForm):

    field_name = forms.ChoiceField(required = True)

    def __init__(self, *args, **kwargs):
        super(FieldRuleAuthorityForm, self).__init__( *args, **kwargs)

        all_authority_fields = Authority._meta.get_fields()

        authority_choices = []
        for field in all_authority_fields:
            authority_choices.append((field.name, field.name))
        authority_choices.sort()
        self.fields['field_name'].choices = authority_choices

    class Meta(object):
        model = FieldRule
        fields = [
            'field_action', 'field_name',
        ]


class UserModuleRuleForm(forms.ModelForm):
    class Meta(object):
        model = UserModuleRule
        fields = [
            'module_action',
        ]


class AttributeForm(forms.ModelForm):
    description = forms.CharField(widget=forms.widgets.Textarea({'rows': '3'}), required=False)
    type_controlled = forms.ModelChoiceField(queryset=AttributeType.objects.all(), required=False)
    record_status_value = forms.ChoiceField(choices=CuratedMixin.STATUS_CHOICES)

    class Meta(object):
        model = Attribute

        fields = [
            'type_controlled',
            'description',
            'value_freeform',
            'record_status_value',
            'record_status_explanation',
            'record_history'
        ]

    def __init__(self, *args, **kwargs):
        super(AttributeForm, self).__init__(*args, **kwargs)
        # if self.instance.id:
        #     self.fields['type_controlled'].widget.attrs['disabled'] = True

        if not self.is_bound:
            if not self.fields['record_status_value'].initial:
                self.fields['record_status_value'].initial = CuratedMixin.ACTIVE

    def save(self, *args, **kwargs):
        if self.instance.id:
            self.fields['type_controlled'].initial = self.instance.type_controlled
        return super(AttributeForm, self).save(*args, **kwargs)


class BulkActionForm(forms.Form):
    def apply(self, user, filter_params_raw, extra=None):
        selected_actions = self.cleaned_data.get('action')
        tasks = []
        for action_name in selected_actions:
            action_value = self.cleaned_data.get(action_name)
            extra_data = {
                k.split('__')[1]: v for k, v in list(self.cleaned_data.items())
                if k.startswith(action_name) and not k == action_name and '__' in k
            }
            if extra:
                extra_data.update(extra)
            # Load and instantiate the corresponding action class.
            action = getattr(actions, action_name)()    # Object is callable.
            tasks.append(action.apply(user, filter_params_raw, action_value, **extra_data))
        return tasks


# Emulates django's modelform_factory
def bulk_action_form_factory(form=BulkActionForm, **kwargs):
    attrs = {}    # For the form's Meta inner class.

    # For the Media inner class.
    media_attrs = {'js': ('curation/js/bulkaction.js', )}
    queryset = kwargs.pop('queryset', None)
    object_type = kwargs.pop('object_type', 'CITATION')

    parent = (object,)
    if hasattr(form, 'Meta'):
        parent = (form.Meta, object)
    Meta = type(str('Meta'), parent, attrs)

    form_class_attrs = {'Meta': Meta}
    action_choices = []
    extra_data = {}
    # hack until we also make tracking status work
    avail_actions = actions.AVAILABLE_ACTIONS_AUTHORITY if object_type == 'AUTHORITY' else actions.AVAILABLE_ACTIONS
    for action_class in avail_actions:
        if hasattr(action_class, 'extra_js'):
            media_attrs['js'] = tuple(list(media_attrs['js']) + [action_class.extra_js])

        if hasattr(action_class, 'get_extra_data'):
            extra_data[action_class.__name__] = action_class.get_extra_data(queryset=queryset)
        action = action_class()
        action_choices.append((action_class.__name__, action.label))
        form_class_attrs[action_class.__name__] = action.get_value_field(required=False)
        extras = action.get_extra_fields()
        if extras:
            form_class_attrs.update({'%s__%s' % (action_class.__name__, name): field for name, field in extras})

    form_class_attrs['Media'] = type(str('Media'), (object,), media_attrs)
    form_class_attrs['extra_data'] = extra_data
    form_class_attrs['action'] = forms.MultipleChoiceField(choices=action_choices)
    form_class_attrs['filters'] = forms.CharField(widget=forms.widgets.HiddenInput())
    return type(form)('BulkChangeForm', (form,), form_class_attrs)


class CitationCollectionForm(forms.ModelForm):
    filters = forms.CharField(widget=forms.widgets.HiddenInput())
    class Meta(object):
        model = CitationCollection
        exclude = ('created', 'createdBy', 'citations')

class AuthorityCollectionForm(forms.ModelForm):
    filters = forms.CharField(widget=forms.widgets.HiddenInput())
    class Meta(object):
        model = AuthorityCollection
        exclude = ('created', 'createdBy', 'authorities')

class AARSetForm(forms.ModelForm):
    class Meta(object):
        model = AARSet
        fields = ['name', 'description']

class AARelationTypeForm(forms.ModelForm):
    class Meta(object):
        model = AARelationType
        fields = ['name', 'description', 'relation_type_controlled', 'base_type', 'aarset']

class SelectCitationCollectionForm(forms.Form):
    collection = forms.ModelChoiceField(queryset=CitationCollection.objects.all())
    filters = forms.CharField(widget=forms.widgets.HiddenInput())

class SelectAuthorityCollectionForm(forms.Form):
    collection = forms.ModelChoiceField(queryset=AuthorityCollection.objects.all())
    filters = forms.CharField(widget=forms.widgets.HiddenInput())

class ExportCitationsForm(forms.Form):
    export_name = forms.CharField(help_text='This tag will be added to the export filename')
    export_format = forms.ChoiceField(choices=[('CSV', 'Comma-separated values (CSV)'), ('EBSCO_CSV', 'Comma-separated values (CSV) in EBSCO format (disregard column selection below)'), ('ITEM_COUNT', 'Export for Item Counts'), ('SWP_ANALYSIS', "Export for SPW Analysis")])
    export_linked_records = forms.BooleanField(label="Export linked records (make sure that the 'Link to Record' Field is selected in the field list)", required=False)
    export_metadata = forms.BooleanField(label="Export metadata", required=False)
    use_pipe_delimiter = forms.BooleanField(label='Use "||" to separate related authority and citation fields', required=False)
    fields = forms.MultipleChoiceField(choices=[(c.slug, c.label) for c in export.CITATION_COLUMNS], required=False)
    filters = forms.CharField(widget=forms.widgets.HiddenInput())
    # compress_output = forms.BooleanField(required=False, initial=True,
    #                                      help_text="If selected, the output"
    #                                      " will be gzipped.")

    def clean_fields(self):
        field_data = self.cleaned_data['fields']
        export_type = self.cleaned_data['export_format']
        if export_type == 'CSV':
            if not field_data:
                raise forms.ValidationError("Please select fields to export.")

        return field_data

class ExportAuthorityForm(forms.Form):
    export_name = forms.CharField(help_text='This tag will be added to the export filename')
    export_format = forms.ChoiceField(choices=[('CSV', 'Comma-separated values (CSV)')])
    export_metadata = forms.BooleanField(label="Export metadata", required=False)
    fields = forms.MultipleChoiceField(choices=[(c.slug, c.label) for c in export_authority.AUTHORITY_COLUMNS])
    filters = forms.CharField(widget=forms.widgets.HiddenInput())

class BulkChangeCSVForm(forms.Form):
    csvFile = forms.FileField()
    NO_CHOICE = None
    CREATE_ATTR = 'CRATT'
    UPDATE_ATTR = 'UPATT'
    CREATE_LINKED_DATA = 'CRLD'
    CREATE_ACRELATIONS = 'CRACR'
    CREATE_AARELATIONS = 'CRAAR'
    CREATE_CCRELATIONS = 'CRCCR'
    CREATE_AUTHORITIES = 'CRAUTH'
    CREATE_CITATIONS = 'CRCIT'
    MERGE_AUTHORITIES = 'MGAUTH'
    CHOICES = [
        (NO_CHOICE, '-------------'),
        (CREATE_ATTR, 'Create Attributes'),
        (UPDATE_ATTR, 'Update Elements'),
        (CREATE_LINKED_DATA, 'Create Linked Data'),
        (CREATE_ACRELATIONS, 'Create ACRelations'),
        (CREATE_AARELATIONS, 'Create AARelations'),
        (CREATE_CCRELATIONS, 'Create CCRelations'),
        (CREATE_AUTHORITIES, 'Create Authorities'),
        (CREATE_CITATIONS, 'Create Citations'),
        (MERGE_AUTHORITIES, 'Duplicate Authority Merge and Redirect'),
    ]
    action = forms.ChoiceField(choices=CHOICES)
