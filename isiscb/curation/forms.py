from django import forms

from isisdata.models import *



class ISODateValueForm(forms.ModelForm):
    value = forms.CharField()

    def __init__(self, *args, **kwargs):
        super(ISODateValueForm, self).__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance:
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
        print self.instance
        print self.instance.value
        print self.cleaned_data
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
