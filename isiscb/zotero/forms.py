from __future__ import unicode_literals
from builtins import object
from django import forms

from zotero.models import *


class ImportAccessionForm(forms.ModelForm):
    """
    Used to create a :class:`.ImportAccession`\.
    """

    zotero_rdf = forms.FileField()
    ingest_to = forms.ModelChoiceField(queryset=Dataset.objects.all(),
                                       empty_label='No dataset')

    def __init__(self, tenant, *args, **kwargs):
        super(ImportAccessionForm, self).__init__(*args, **kwargs)
        if tenant:
            self.fields['ingest_to'].queryset = Dataset.objects.filter(owning_tenant=tenant)

    
    class Meta(object):
        model = ImportAccession
        fields = ['name', 'ingest_to', 'zotero_rdf', 'owning_tenant']
        widgets = {'owning_tenant': forms.HiddenInput()}


class DraftAuthorityForm(forms.ModelForm):
    class Meta(object):
        model = DraftAuthority
        fields = ['name', 'type_controlled']
