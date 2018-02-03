from __future__ import absolute_import

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
    REVIEWED_BY = 'RB'
    RESPONDS_TO = 'RE'
    ASSOCIATED_WITH = 'AS'
    TYPE_CHOICES = (
        (INCLUDES_CHAPTER, 'Includes Chapter'),
        (INCLUDES_SERIES_ARTICLE, 'Includes Series Article'),
        (RESPONDS_TO, 'Responds To'),
        (ASSOCIATED_WITH, 'Is Associated With'),
        (REVIEWED_BY, 'Is Reviewed By')
    )
    type_controlled = forms.ChoiceField(choices=TYPE_CHOICES)

    class Meta:
        model = CCRelation
        fields = [
            'type_controlled', 'data_display_order', 'subject',
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
        subject_id = self.cleaned_data.get('subject', None)
        if subject_id:
            self.cleaned_data['subject'] = Citation.objects.get(pk=subject_id)

        object_id = self.cleaned_data.get('object', None)
        if object_id:
            self.cleaned_data['object'] = Citation.objects.get(pk=object_id)



class ACRelationForm(forms.ModelForm):
    authority = forms.CharField(widget=forms.HiddenInput(), required=False)
    citation = forms.CharField(widget=forms.HiddenInput(), required=False)
    """We will set these dynamically in the rendered form."""

    record_status_value = forms.ChoiceField(choices=CuratedMixin.STATUS_CHOICES, required=False)

    AUTHOR = 'AU'
    EDITOR = 'ED'
    ADVISOR = 'AD'
    CONTRIBUTOR = 'CO'
    TRANSLATOR = 'TR'
    SUBJECT = 'SU'
    CATEGORY = 'CA'
    PUBLISHER = 'PU'
    SCHOOL = 'SC'
    PERIODICAL = 'PE'
    COMMITTEE_MEMBER = 'CM'
    TYPE_CHOICES = (
        (AUTHOR, 'Author'),
        (EDITOR, 'Editor'),
        (ADVISOR, 'Advisor'),
        (CONTRIBUTOR, 'Contributor'),
        (TRANSLATOR, 'Translator'),
        (SUBJECT, 'Subject'),
        (CATEGORY, 'Category'),
        (PUBLISHER, 'Publisher'),
        (SCHOOL, 'School'),
        (PERIODICAL, 'Periodical'),
        (COMMITTEE_MEMBER, 'Committee Member'),
    )
    type_controlled = forms.ChoiceField(choices=TYPE_CHOICES, required=False)

    confidence_measure = forms.TypedChoiceField(**{
        'choices': [
            (1.0, 'Certain/very likely'),
            (0.5, 'Likely'),
            (0.0, 'Unsure'),
        ],
        'coerce': float,
        'required': True,
    })

    class Meta:
        model = ACRelation
        fields = [
            'type_controlled',
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

            if self.instance.type_controlled in [Citation.REVIEW, Citation.CHAPTER, Citation.ARTICLE, Citation.ESSAY_REVIEW]:
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

    abstract = forms.CharField(widget=forms.widgets.Textarea({'rows': '7'}), required=False)
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
            'type_controlled', 'record_status_value',
            'record_status_explanation', 'administrator_notes'
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
    belongs_to = forms.ModelChoiceField(queryset=Dataset.objects.all(), label='Dataset', required=False)

    class Meta:
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

    class Meta:
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

    class Meta:
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

    class Meta:
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

    class Meta:
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


    class Meta:
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
        # if self.instance.id:
        #     self.fields['type_controlled'].widget.attrs['disabled'] = True

        if not self.is_bound:
            if not self.fields['record_status_value'].initial:
                self.fields['record_status_value'].initial = CuratedMixin.ACTIVE

    def save(self, *args, **kwargs):
        if self.instance.id:
            self.fields['type_controlled'].initial = self.instance.type_controlled
        super(AttributeForm, self).save(*args, **kwargs)


class BulkActionForm(forms.Form):
    def apply(self, user, filter_params_raw):
        selected_actions = self.cleaned_data.get('action')
        tasks = []
        for action_name in selected_actions:
            action_value = self.cleaned_data.get(action_name)
            extra_data = {
                k.split('__')[1]: v for k, v in self.cleaned_data.iteritems()
                if k.startswith(action_name) and not k == action_name and '__' in k
            }
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

    parent = (object,)
    if hasattr(form, 'Meta'):
        parent = (form.Meta, object)
    Meta = type(str('Meta'), parent, attrs)

    form_class_attrs = {'Meta': Meta}
    action_choices = []
    extra_data = {}
    for action_class in actions.AVAILABLE_ACTIONS:
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
    class Meta:
        model = CitationCollection
        exclude = ('created', 'createdBy', 'citations')


class SelectCitationCollectionForm(forms.Form):
    collection = forms.ModelChoiceField(queryset=CitationCollection.objects.all())
    filters = forms.CharField(widget=forms.widgets.HiddenInput())


class ExportCitationsForm(forms.Form):
    export_name = forms.CharField(help_text='This tag will be added to the export filename')
    export_format = forms.ChoiceField(choices=[('CSV', 'Comma-separated values (CSV)')])
    export_linked_records = forms.BooleanField(label='Export linked records', required=False)
    fields = forms.MultipleChoiceField(choices=map(lambda c: (c.slug, c.label), export.CITATION_COLUMNS))
    filters = forms.CharField(widget=forms.widgets.HiddenInput())
    # compress_output = forms.BooleanField(required=False, initial=True,
    #                                      help_text="If selected, the output"
    #                                      " will be gzipped.")

class ExportAuthorityForm(forms.Form):
    export_name = forms.CharField(help_text='This tag will be added to the export filename')
    export_format = forms.ChoiceField(choices=[('CSV', 'Comma-separated values (CSV)')])
    fields = forms.MultipleChoiceField(choices=map(lambda c: (c.slug, c.label), export_authority.AUTHORITY_COLUMNS))
    filters = forms.CharField(widget=forms.widgets.HiddenInput())
