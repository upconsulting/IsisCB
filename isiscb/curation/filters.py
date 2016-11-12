import django_filters
from django_filters.fields import Lookup
from django_filters.filterset import STRICTNESS
from django.db.models import Q
from django import forms

from isisdata.models import *
from zotero.models import ImportAccession
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


class ChoiceMethodFilter(django_filters.MethodFilter, django_filters.ChoiceFilter):
    pass

def filter_in_collections(queryset, value):
    if not value:
        return queryset
    q = Q()
    for collection in value:
        q |= Q(in_collections=collection)

    return queryset.filter(q)


class CitationFilter(django_filters.FilterSet):
    strict = STRICTNESS.RETURN_NO_RESULTS

    id = django_filters.MethodFilter(name='id', lookup_type='exact')
    title = django_filters.MethodFilter(name='title', lookup_type='icontains')
    type_controlled = django_filters.ChoiceFilter(choices=[('', 'All')] + list(Citation.TYPE_CHOICES))
    publication_date_from = django_filters.MethodFilter()
    publication_date_to = django_filters.MethodFilter()
    abstract = django_filters.MethodFilter(name='abstract', lookup_type='icontains')
    description = django_filters.MethodFilter(name='description', lookup_type='icontains')

    author_or_editor = django_filters.MethodFilter()
    periodical = django_filters.MethodFilter()
    publisher = django_filters.MethodFilter()
    subject = django_filters.MethodFilter()

    record_status = django_filters.ChoiceFilter(name='record_status_value', choices=[('', 'All')] + list(CuratedMixin.STATUS_CHOICES))
    in_collections = django_filters.CharFilter(widget=forms.HiddenInput(), action=filter_in_collections)
    zotero_accession = django_filters.CharFilter(widget=forms.HiddenInput())
    # language = django_filters.ModelChoiceFilter(name='language', queryset=Language.objects.all())

    # order = ChoiceMethodFilter(name='order', choices=order_by)

    def __init__(self, *args, **kwargs):
        super(CitationFilter, self).__init__(*args, **kwargs)
        in_coll = self.data.get('in_collections', None)
        if in_coll:
            try:
                collection = CitationCollection.objects.get(pk=in_coll)
                if collection:
                    self.collection_name = collection.name
            except CitationCollection.DoesNotExist:
                self.collection_name = "Collection could not be found."

        zotero_acc = self.data.get('zotero_accession', None)
        if zotero_acc:
            try:
                accession = ImportAccession.objects.get(pk=zotero_acc)
                if accession:
                    self.zotero_accession_name = accession.name
            except ImportAccession.DoesNotExist:
                self.zotero_accession_name = "Zotero accession could not be found."

    class Meta:
        model = Citation
        fields = [
            'id', 'title', 'abstract', 'description',
            'publication_date_from', 'publication_date_to',
            'author_or_editor', 'periodical', 'record_status',
            'belongs_to', 'zotero_accession', 'in_collections',
        ]
        order_by = [
            ('publication_date', 'Publication date (ascending)'),
            ('-publication_date', 'Publication date (descending)'),
            ('title_for_sort', 'Title (ascending)'),
            ('-title_for_sort', 'Title (descending)')
        ]

    # def filter_order(self, queryset, value):
    #     if not value:
    #         return queryset
    #     if value.endswith('title'):
    #         return queryset.order_by('%srelations_from__subject__title' % ('-' if value.startswith('-') else ''),
    #                                           '%srelations_to__subject__title' % ('-' if value.startswith('-') else '')).order_by(value)
    #     return queryset.order_by(value)

    def filter_id(self, queryset, value):
        if not value:
            return queryset

        ids = [i.strip() for i in value.split(',')]
        queryset = queryset.filter(pk__in=ids)
        return queryset

    def filter_title(self, queryset, value):
        if not value:
            return queryset
        for part in value.split():
            queryset = queryset.filter(title__icontains=part)
        return queryset

    def filter_abstract(self, queryset, value):
        if not value:
            return queryset
        for part in value.split():
            queryset = queryset.filter(abstract__icontains=part)
        return queryset

    def filter_description(self, queryset, value):
        if not value:
            return queryset
        for part in value.split():
            queryset = queryset.filter(description__icontains=part)
        return queryset

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
        for part in value.split():
            queryset = queryset.filter(
                        acrelation__authority__name__icontains=part,
                        acrelation__type_controlled__in=[
                                    ACRelation.AUTHOR,
                                    ACRelation.EDITOR])
        return queryset

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

    def filter_subject(self, queryset, value):
        if not value:
            return queryset
        return queryset.filter(acrelation__authority__name__icontains=value,
                               acrelation__type_controlled=ACRelation.SUBJECT)


class AuthorityFilter(django_filters.FilterSet):
    strict = STRICTNESS.RETURN_NO_RESULTS

    id = django_filters.CharFilter(name='id', lookup_type='exact')
    name = django_filters.MethodFilter()
    type_controlled = django_filters.ChoiceFilter(choices=[('', 'All')] + list(Authority.TYPE_CHOICES))
    description = django_filters.CharFilter(name='description', lookup_type='icontains')
    classification_system = django_filters.ChoiceFilter(name='classification_system', choices=[('', 'All')] + list(Authority.CLASS_SYSTEM_CHOICES))
    classification_code = django_filters.AllValuesFilter(name='classification_code')
    classification_hierarchy = django_filters.AllValuesFilter(name='classification_hierarchy')
    linked_data = django_filters.MethodFilter()

    record_status_value = django_filters.ChoiceFilter(name='record_status_value', choices=[('', 'All')] + list(CuratedMixin.STATUS_CHOICES))

    class Meta:
        model = Authority
        fields = [
            'id', 'name', 'type_controlled', 'description',
            'classification_system', 'classification_code',
            'classification_hierarchy', 'zotero_accession',
            'belongs_to']

        order_by = [
            ('', 'None'),
            ('name_for_sort', 'Name (ascending)'),
            ('-name_for_sort', 'Name (descending)')
        ]


    def filter_name(self, queryset, value):
        if not value:
            return queryset
        for part in value.split():
            queryset = queryset.filter(name__icontains=part)

        return queryset

    def filter_linked_data(self, queryset, value):
        if not value:
            return queryset
        authority_ids = LinkedData.objects\
                            .filter(universal_resource_name__contains=value)\
                            .values_list('authorities__id', flat=True)\
                            .distinct()

        if len(authority_ids) == 1 and authority_ids[0] is None:
            return queryset.none()
        return queryset.filter(pk__in=authority_ids)
