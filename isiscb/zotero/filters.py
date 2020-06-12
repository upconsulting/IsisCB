from __future__ import unicode_literals
from builtins import object
import django_filters
from django_filters.fields import Lookup
from django.db.models import Q, Count

from zotero.models import *
from isisdata.helper_methods import strip_punctuation
import six
import iso8601

from django_filters import filters

filters.LOOKUP_TYPES = [
    ('', '---------'),
    ('exact', 'Is equal to'),
    ('not_exact', 'Is not equal to'),
    ('lt', 'Lesser than'),
    ('gt', 'Greater than'),
    ('gte', 'Greater than or equal to'),
    ('lte', 'Lesser than or equal to'),
    ('startswith', 'Starts with'),
    ('endswith', 'Ends with'),
    ('icontains', 'Contains'),
    ('not_contains', 'Does not contain'),
]

from django.core.exceptions import ValidationError
# import iso8601


class ImportAccesionFilter(django_filters.FilterSet):
    processed = django_filters.BooleanFilter(field_name='processed')
    name = django_filters.CharFilter(lookup_expr='istartswith')
    imported_on_or_after = django_filters.CharFilter(method='filter_imported_on_or_after')
    imported_on_or_before = django_filters.CharFilter(method='filter_imported_on_or_before')
    imported_by = django_filters.ModelChoiceFilter(queryset=User.objects.filter(importaccession__id__isnull=False).distinct('id'))
    #
    def filter_imported_on_or_after(self, queryset, name, value):
        try:
            queryset = queryset.filter(imported_on__date__gte=value)
        except Exception as E:
            return queryset

        return queryset

    def filter_imported_on_or_before(self, queryset, name, value):
        try:
            queryset = queryset.filter(imported_on__date__lte=value)
        except Exception as E:
            return queryset

        return queryset


    class Meta(object):
        model = ImportAccession
        fields = ['id', 'name', 'processed', 'imported_on_or_before',
                  'imported_on_or_after', 'imported_by', 'ingest_to']

        o = django_filters.filters.OrderingFilter(
            # tuple-mapping retains order
            fields=(
                ('imported_on', 'imported_on'),
            ),

            # labels do not need to retain order
            field_labels={
                'imported_on': 'Date imported',
            }
        )
