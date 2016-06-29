from django import forms

from isisdata.models import *


class CCRelationForm(forms.ModelForm):
    subject = forms.CharField(widget=forms.HiddenInput())
    object = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = CCRelation
        fields = [
            'type_controlled', 'description', 'data_display_order', 'subject',
            'object', 'record_status_value', 'record_status_explanation'
        ]

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

    class Meta:
        model = ACRelation
        fields = [
            'type_controlled', 'type_broad_controlled',
            'name_for_display_in_citation', 'data_display_order',
            'confidence_measure', 'authority', 'citation',
            'record_status_value', 'record_status_explanation'
        ]

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
    extent_note = forms.CharField(widget=forms.widgets.Textarea({'rows': '1'}))

    class Meta:
        model = PartDetails
        exclude =['volume',]


class CitationForm(forms.ModelForm):
    abstract = forms.CharField(widget=forms.widgets.Textarea({'rows': '3'}), required=False)
    description = forms.CharField(widget=forms.widgets.Textarea({'rows': '3'}), required=False)

    additional_titles = forms.CharField(widget=forms.widgets.Textarea({'rows': '2'}), required=False)
    edition_details = forms.CharField(widget=forms.widgets.Textarea({'rows': '2'}), required=False)
    physical_details = forms.CharField(widget=forms.widgets.Textarea({'rows': '2'}), required=False)

    language = forms.ModelMultipleChoiceField(queryset=Language.objects.all(), required=False)

    dataset = forms.ChoiceField(choices=[(d, d) for d in Citation.objects.order_by().values_list('dataset', flat=True).distinct()])

    class Meta:
        model = Citation
        fields = [
            'type_controlled', 'title', 'description', 'edition_details',
              'physical_details', 'language', 'abstract', 'additional_titles',
              'book_series', 'record_status_value', 'record_status_explanation',
              'dataset',
        ]


class AuthorityForm(forms.ModelForm):
    description = forms.CharField(widget=forms.widgets.Textarea({'rows': '3'}), required=False)

    class Meta:
        model = Authority
        fields = [
            'type_controlled', 'name', 'description', 'classification_system',
            'classification_code', 'classification_hierarchy',
            'record_status_value', 'record_status_explanation',
        ]


class PersonForm(forms.ModelForm):
    description = forms.CharField(widget=forms.widgets.Textarea({'rows': '3'}), required=False)

    class Meta:
        model = Person
        fields = [
            'personal_name_last', 'personal_name_first', 'personal_name_suffix',
            'personal_name_preferred',
        ]

class RoleForm(forms.ModelForm):

    class Meta:
        model = IsisCBRole
        fields = [
            'name', 'description',
        ]

class DatasetRuleForm(forms.ModelForm):
    dataset_values = Citation.objects.values_list('dataset').distinct()

    choices = []
    for value in dataset_values:
        if value[0]:
            choices.append((value[0], value[0]))

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

class FieldRuleCitationForm(forms.ModelForm):

    all_citation_fields = Citation._meta.get_fields()

    choices = []
    for field in all_citation_fields:
        choices.append((field.name, field.name))


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

    field_name = forms.ChoiceField(choices = authority_choices, required = True)

    class Meta:
        model = FieldRule
        fields = [
            'field_action', 'field_name',
        ]

class AttributeForm(forms.ModelForm):
    description = forms.CharField(widget=forms.widgets.Textarea({'rows': '3'}), required=False)
    type_controlled = forms.ModelChoiceField(queryset=AttributeType.objects.all(), required=False)

    class Meta:
        model = Attribute

        fields = [
            'type_controlled',
            'description',
            'value_freeform',
        ]

    def __init__(self, *args, **kwargs):
        super(AttributeForm, self).__init__(*args, **kwargs)
        if self.instance.id:
            self.fields['type_controlled'].widget.attrs['disabled'] = True

    def save(self, *args, **kwargs):
        if self.instance.id:
            self.fields['type_controlled'].initial = self.instance.type_controlled
        super(AttributeForm, self).save(*args, **kwargs)
