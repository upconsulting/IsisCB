from django import forms

from zotero.models import *


class ImportAccessionForm(forms.ModelForm):
    """
    Used to create a :class:`.ImportAccession`\.
    """
    
    zotero_rdf = forms.FileField()

    class Meta:
        model = ImportAccession
        fields = ['name', 'zotero_rdf']
