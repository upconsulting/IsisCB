from __future__ import absolute_import

from django import forms

from isisdata.models import *

import rules


class CCRelationForm(forms.ModelForm):
    subject = forms.CharField(widget=forms.HiddenInput())
    object = forms.CharField(widget=forms.HiddenInput())
    """We will set these dynamically in the rendered form."""

    record_status_value = forms.ChoiceField(choices=CuratedMixin.STATUS_CHOICES, required=False)

    class Meta:
        model = CCRelation
        fields = [
            'type_controlled', 'description', 'data_display_order', 'subject',
            'object', 'record_status_value', 'record_status_explanation',
            'administrator_notes',
        ]
        labels = {
            'administrator_notes': 'Staff notes'
        }

    def __init__(self, *args, **kwargs):
        super(CCRelationForm, self).__init__(*args, **kwargs)
        if not self.is_bound:
            if not self.fields['record_status_value'].initial:
                self.fields['record_status_value'].initial = CuratedMixin.ACTIVE

    def clean(self):
        super(CCRelationForm, self).clean()
        subject_id = self.cleaned_data['subject']
        self.cleaned_data['subject'] = Citation.objects.get(pk=subject_id)

        object_id = self.cleaned_data['object']
        self.cleaned_data['object'] = Citation.objects.get(pk=object_id)



class ACRelationForm(forms.ModelForm):
    authority = forms.CharField(widget=forms.HiddenInput())
    citation = forms.CharField(widget=forms.HiddenInput())
    """We will set these dynamically in the rendered form."""

    record_status_value = forms.ChoiceField(choices=CuratedMixin.STATUS_CHOICES, required=False)

    class Meta:
        model = ACRelation
        fields = [
            'type_controlled', 'type_broad_controlled',
            'name_for_display_in_citation', 'data_display_order',
            'confidence_measure', 'authority', 'citation',
            'record_status_value', 'record_status_explanation',
            'administrator_notes'
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
        authority_id = self.cleaned_data['authority']
        self.cleaned_data['authority'] = Authority.objects.get(pk=authority_id)
        citation_id = self.cleaned_data['citation']
        self.cleaned_data['citation'] = Citation.objects.get(pk=citation_id)

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

    class Meta:
        model = ISODateValue
        fields = []


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

    class Meta:
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


class CitationForm(forms.ModelForm):

    def __init__(self, user, *args, **kwargs):
        super(CitationForm, self).__init__( *args, **kwargs)
        self.user = user

        if not self.is_bound:
            if not self.fields['record_status_value'].initial:
                self.fields['record_status_value'].initial = CuratedMixin.ACTIVE

        # disable fields user doesn't have access to
        if self.instance.pk:
            # Don't let the user change type_controlled.
            #self.fields['type_controlled'].widget.attrs['readonly'] = True
            #self.fields['type_controlled'].widget.attrs['disabled'] = True
            self.fields['title'].widget.attrs['placeholder'] = "No title"
            self.fields['type_controlled'].widget = forms.widgets.HiddenInput()

            if self.instance.type_controlled in [Citation.REVIEW, Citation.CHAPTER, Citation.ARTICLE]:
                self.fields['physical_details'].widget = forms.widgets.HiddenInput()
                self.fields['book_series'].widget = forms.widgets.HiddenInput()

            if self.instance.type_controlled in [Citation.THESIS]:
                self.fields['book_series'].widget = forms.widgets.HiddenInput()

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

    abstract = forms.CharField(widget=forms.widgets.Textarea({'rows': '3'}), required=False)
    description = forms.CharField(widget=forms.widgets.Textarea({'rows': '3'}), required=False)
    record_history = forms.CharField(widget=forms.widgets.Textarea({'rows': '3'}), required=False)

    additional_titles = forms.CharField(widget=forms.widgets.Textarea({'rows': '2'}), required=False)
    edition_details = forms.CharField(widget=forms.widgets.Textarea({'rows': '2'}), required=False)
    physical_details = forms.CharField(widget=forms.widgets.Textarea({'rows': '2'}), required=False)

    language = forms.ModelMultipleChoiceField(queryset=Language.objects.all(), required=False)

    belongs_to = forms.ModelChoiceField(queryset=Dataset.objects.all(), label='Dataset', required=False)
    record_status_value = forms.ChoiceField(choices=CuratedMixin.STATUS_CHOICES, required=False)

    class Meta:
        model = Citation
        fields = [
            'type_controlled', 'title', 'description', 'edition_details',
              'physical_details', 'abstract', 'additional_titles',
              'book_series', 'record_status_value', 'record_status_explanation',
              'belongs_to', 'administrator_notes', 'record_history',
        ]
        labels = {
            'belongs_to': 'Dataset',
            'administrator_notes': 'Staff notes'
        }

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

    class Meta:
        model = LinkedData
        fields = [
            'universal_resource_name', 'resource_name', 'url',
            'type_controlled', 'record_status_value', 'administrator_notes'
        ]

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

    class Meta:
        model = Authority
        fields = [
            'type_controlled', 'name', 'description', 'classification_system',
            'classification_code', 'classification_hierarchy',
            'record_status_value', 'record_status_explanation', 'redirect_to',
            'administrator_notes', 'record_history',
        ]

        labels = {
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

    class Meta:
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

    class Meta:
        model = IsisCBRole
        fields = [
            'name', 'description',
        ]


class DatasetRuleForm(forms.ModelForm):
    dataset_values = Dataset.objects.all()

    choices = set()
    for ds in dataset_values:
        choices.add((ds.pk, ds.name))

    dataset = forms.ChoiceField(choices = choices, required=True)

    class Meta:
        model = DatasetRule

        fields = [
            'dataset', 'role'
        ]


class AddRoleForm(forms.Form):
    roles = IsisCBRole.objects.all()

    choices = []
    for role in roles:
        choices.append((role.pk, role.name))

    role = forms.ChoiceField(choices = choices, required=True)

class CRUDRuleForm(forms.ModelForm):

    class Meta:
        model = CRUDRule
        fields = [
            'crud_action'
        ]
        labels = {
            'crud_action': 'Allowed Action',
        }

class FieldRuleCitationForm(forms.ModelForm):

    all_citation_fields = Citation._meta.get_fields()

    choices = []
    for field in all_citation_fields:
        choices.append((field.name, field.name))
    choices.sort()

    field_name = forms.ChoiceField(choices = choices, required = True)

    class Meta:
        model = FieldRule
        fields = [
            'field_action', 'field_name',
        ]

class FieldRuleAuthorityForm(forms.ModelForm):
    all_authority_fields = Authority._meta.get_fields()

    authority_choices = []
    for field in all_authority_fields:
        authority_choices.append((field.name, field.name))
    authority_choices.sort()

    field_name = forms.ChoiceField(choices = authority_choices, required = True)

    class Meta:
        model = FieldRule
        fields = [
            'field_action', 'field_name',
        ]


class UserModuleRuleForm(forms.ModelForm):
    class Meta:
        model = UserModuleRule
        fields = [
            'module_action',
        ]


class AttributeForm(forms.ModelForm):
    description = forms.CharField(widget=forms.widgets.Textarea({'rows': '3'}), required=False)
    type_controlled = forms.ModelChoiceField(queryset=AttributeType.objects.all(), required=False)
    record_status_value = forms.ChoiceField(choices=CuratedMixin.STATUS_CHOICES)

    class Meta:
        model = Attribute

        fields = [
            'type_controlled',
            'description',
            'value_freeform',
            'record_status_value',
            'record_status_explanation'
        ]

    def __init__(self, *args, **kwargs):
        super(AttributeForm, self).__init__(*args, **kwargs)
        if self.instance.id:
            self.fields['type_controlled'].widget.attrs['disabled'] = True

        if not self.is_bound:
            if not self.fields['record_status_value'].initial:
                self.fields['record_status_value'].initial = CuratedMixin.ACTIVE

    def save(self, *args, **kwargs):
        if self.instance.id:
            self.fields['type_controlled'].initial = self.instance.type_controlled
        super(AttributeForm, self).save(*args, **kwargs)
