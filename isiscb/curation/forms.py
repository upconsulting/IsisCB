from django import forms

from isisdata.models import *


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

    class Meta:
        model = Citation
        fields = [
            'type_controlled', 'title', 'description', 'edition_details',
              'physical_details', 'language', 'abstract', 'additional_titles',
              'book_series', 'record_status_value', 'record_status_explanation',
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

    
