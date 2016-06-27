import django_filters
from django_filters.fields import Lookup
from django_filters.filterset import STRICTNESS
from django.db.models import Q

from isisdata.models import *
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


class CitationFilter(django_filters.FilterSet):
    strict = STRICTNESS.RAISE_VALIDATION_ERROR

    id = django_filters.CharFilter(name='id', lookup_type='exact')
    title = django_filters.CharFilter(name='title', lookup_type='icontains')
    type_controlled = django_filters.ChoiceFilter(choices=[('', 'All')] + list(Citation.TYPE_CHOICES))
    publication_date_from = django_filters.MethodFilter()
    publication_date_to = django_filters.MethodFilter()
    abstract = django_filters.CharFilter(name='abstract', lookup_type='icontains')
    description = django_filters.CharFilter(name='description', lookup_type='icontains')

    author_or_editor = django_filters.MethodFilter()
    periodical = django_filters.MethodFilter()
    publisher = django_filters.MethodFilter()
    subject = django_filters.MethodFilter()
    # language = django_filters.ModelChoiceFilter(name='language', queryset=Language.objects.all())

    class Meta:
        model = Citation
        fields = [
            'id', 'title', 'abstract', 'description',
            'publication_date_from', 'publication_date_to',
            'author_or_editor', 'periodical',
        ]
        order_by = [
            ('publication_date', 'Publication date (ascending)'),
            ('-publication_date', 'Publication date (descending)')
        ]

    def filter_publication_date_from(self, queryset, value):
        try:
            date = iso8601.parse_date(value)
        except:
            return queryset
        return queryset.filter(publication_date__gte=date)

    def filter_publication_date_to(self, queryset, value):
        try:
            date = iso8601.parse_date(value)
        except:
            return queryset
        return queryset.filter(publication_date__lte=date)

    def filter_author_or_editor(self, queryset, value):
        if not value:
            return queryset
        return queryset.filter(acrelation__authority__name__istartswith=value,
                               acrelation__type_controlled__in=[
                                    ACRelation.AUTHOR,
                                    ACRelation.EDITOR])

    def filter_periodical(self, queryset, value):
        if not value:
            return queryset
        return queryset.filter(acrelation__authority__name__icontains=value,
                               acrelation__type_controlled__in=[
                                    ACRelation.PERIODICAL,
                                    ACRelation.BOOK_SERIES])

    def filter_publisher(self, queryset, value):
        if not value:
            return queryset
        return queryset.filter(acrelation__authority__name__icontains=value,
                               acrelation__type_controlled=ACRelation.PUBLISHER)


    def filter_publisher(self, queryset, value):
        if not value:
            return queryset
        return queryset.filter(acrelation__authority__name__icontains=value,
                               acrelation__type_controlled=ACRelation.SUBJECT)



class AuthorityFilter(django_filters.FilterSet):
    strict = STRICTNESS.RAISE_VALIDATION_ERROR

    id = django_filters.CharFilter(name='id', lookup_type='exact')
    name = django_filters.MethodFilter()
    type_controlled = django_filters.ChoiceFilter(choices=[('', 'All')] + list(Authority.TYPE_CHOICES))
    description = django_filters.CharFilter(name='description', lookup_type='icontains')


    class Meta:
        model = Authority
        fields = ['name', 'type_controlled']


    def filter_name(self, queryset, value):
        if not value:
            return queryset
        for part in value.split():
            queryset = queryset.filter(name__icontains=part)

        return queryset
