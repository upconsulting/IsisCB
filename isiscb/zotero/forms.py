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
    
    class Meta(object):
        model = ImportAccession
        fields = ['name', 'ingest_to', 'zotero_rdf', 'tenant']
        widgets = {'tenant': forms.HiddenInput()}


class DraftAuthorityForm(forms.ModelForm):
    class Meta(object):
        model = DraftAuthority
        fields = ['name', 'type_controlled']
