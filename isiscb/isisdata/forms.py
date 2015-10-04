from haystack.forms import FacetedSearchForm
from django import forms
from django.db import models
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy as _

from haystack import connections
from haystack.constants import DEFAULT_ALIAS
from haystack.query import EmptySearchQuerySet, SearchQuerySet
from haystack.utils import get_model_ct

try:
    from django.utils.encoding import smart_text
except ImportError:
    from django.utils.encoding import smart_unicode as smart_text

def model_choices(using=DEFAULT_ALIAS):
    choices = [(get_model_ct(m), capfirst(smart_text(m._meta.verbose_name_plural)))
               for m in connections[using].get_unified_index().get_indexed_models()]
    return sorted(choices, key=lambda x: x[1])

class MyFacetedSearchForm(FacetedSearchForm):
    def __init__(self, *args, **kwargs):
        super(MyFacetedSearchForm, self).__init__(*args, **kwargs)
        # TODO: figure out why this field is defined post-hoc, and whether it
        #  matters.
        #scField = forms.MultipleChoiceField(choices=model_choices(),
        #                                    required=False,
        #                                    label=_('Search In'),
        #                                    widget=forms.CheckboxSelectMultiple)
        scField = forms.CharField(max_length=255, widget=forms.HiddenInput(), initial='isisdata.citation')
        sort_order = forms.CharField(required=False, widget=forms.HiddenInput)

        self.fields['models'] = scField
        self.fields['sort_order'] = sort_order
        self.fields['sort_order'].initial = 'title_for_sort'

        #self.fields['models'].initial = ['isisdata.authority',
        #                                  'isisdata.citation']

    def get_models(self):
        """Return an alphabetical list of model classes in the index."""
        search_models = []

        if self.is_valid():
            #for model in self.cleaned_data['models']:
            #search_models.append(models.get_model(*model.split('.')))
            # if we want the option to select both indexes at the same time we might need above back
            search_models.append(models.get_model(*self.cleaned_data['models'].split('.')))

        return search_models

    def get_sort_order(self):
        sort_order = 'text'

        if self.is_valid():
            sort_order = self.cleaned_data.get('sort_order', 'title_for_sort')
            if not sort_order and self.cleaned_data['models'] == 'isisdata.citation':
                sort_order = 'title_for_sort'
            if not sort_order and self.cleaned_data['models'] == 'isisdata.authority':
                sort_order = 'name'

        return sort_order

    def search(self):
        sqs = super(MyFacetedSearchForm, self).search()
        sort_order = self.get_sort_order()
        return sqs.models(*self.get_models()).order_by(sort_order)
