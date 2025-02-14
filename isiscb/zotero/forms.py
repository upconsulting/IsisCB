from __future__ import unicode_literals
from builtins import object
from django import forms

from zotero.models import *
import curation.permissions_util as p_util


class ImportAccessionForm(forms.ModelForm):
    """
    Used to create a :class:`.ImportAccession`\.
    """

    zotero_rdf = forms.FileField()
    ingest_to = forms.ModelChoiceField(queryset=Dataset.objects.all(), required=True,
                                       empty_label='Please select dataset')

    def __init__(self, tenant, user, *args, **kwargs):
        super(ImportAccessionForm, self).__init__(*args, **kwargs)
        if tenant:
            datasets = p_util.get_writable_dataset_objects(user)
            self.fields['ingest_to'].queryset = datasets
            if tenant.default_dataset in datasets:
                self.fields['ingest_to'].initial = tenant.default_dataset
            else:
                self.fields['ingest_to'].initial = datasets.first()

    
    class Meta(object):
        model = ImportAccession
        fields = ['name', 'ingest_to', 'zotero_rdf', 'owning_tenant']
        widgets = {'owning_tenant': forms.HiddenInput()}


class DraftAuthorityForm(forms.ModelForm):
    class Meta(object):
        model = DraftAuthority
        fields = ['name', 'type_controlled']
