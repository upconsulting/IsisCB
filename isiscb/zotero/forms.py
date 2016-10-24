from django import forms

from zotero.models import *


class ImportAccessionForm(forms.ModelForm):
    """
    Used to create a :class:`.ImportAccession`\.
    """

    zotero_rdf = forms.FileField()
    ingest_to = forms.ModelChoiceField(queryset=Dataset.objects.all(),
                                       empty_label='No dataset')

    class Meta:
        model = ImportAccession
        fields = ['name', 'ingest_to', 'zotero_rdf']


class DraftAuthorityForm(forms.ModelForm):
    class Meta:
        model = DraftAuthority
        fields = ['name', 'type_controlled']
