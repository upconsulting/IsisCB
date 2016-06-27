import django_filters
from django_filters.fields import Lookup


from isisdata.models import *
import six
import iso8601


class CitationFilter(django_filters.FilterSet):
    id = django_filters.CharFilter(name='id', lookup_type='exact')
    title = django_filters.CharFilter(name='title', lookup_type='icontains')
    type_controlled = django_filters.ChoiceFilter(choices=[('', 'All')] + list(Citation.TYPE_CHOICES))
    publication_date_from = django_filters.MethodFilter()
    publication_date_to = django_filters.MethodFilter()
    abstract = django_filters.CharFilter(name='abstract', lookup_type='icontains')
    description = django_filters.CharFilter(name='description', lookup_type='icontains')

    class Meta:
        model = Citation
        fields = [
            'id', 'title', 'abstract', 'description',
            'publication_date_from', 'publication_date_to'
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


class AuthorityFilter(django_filters.FilterSet):
    id = django_filters.CharFilter(name='id', lookup_type='exact')
    name = django_filters.CharFilter(name='name', lookup_type='icontains')
    type_controlled = django_filters.ChoiceFilter(choices=[('', 'All')] + list(Authority.TYPE_CHOICES))
    description = django_filters.CharFilter(name='description', lookup_type='icontains')

    class Meta:
        model = Authority
        fields = ['name', 'type_controlled']
