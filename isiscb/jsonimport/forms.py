from django import forms
from isisdata.models import Dataset
from curation import curation_util as cutil
from curation import permissions_util

class UploadJsonDataForm(forms.Form):
    citations_file = forms.FileField()
    authorities_file = forms.FileField()
    citations_dataset = forms.ModelChoiceField(
        queryset=Dataset.objects.none(),
        required=False,
        empty_label='Use automatic selection',
        label='Default dataset for citations',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    authorities_dataset = forms.ModelChoiceField(
        queryset=Dataset.objects.none(),
        required=False,
        empty_label='Use automatic selection',
        label='Default dataset for authorities',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is None:
            return

        datasets = permissions_util.get_writable_dataset_objects(user)
        tenant = cutil.get_tenant(user)
        if tenant:
            datasets = datasets.filter(owning_tenant=tenant)
        datasets = datasets.order_by('name')
        self.fields['citations_dataset'].queryset = datasets
        self.fields['authorities_dataset'].queryset = datasets