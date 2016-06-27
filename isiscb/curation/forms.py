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

    language = forms.ModelMultipleChoiceField(queryset=Language.objects.all())

    class Meta:
        model = Citation
        fields = ['type_controlled', 'title', 'description', 'edition_details',
                  'physical_details', 'language', 'abstract',
                  'additional_titles', 'book_series']
