import django_filters
from django_filters.fields import Lookup
from django_filters.filterset import STRICTNESS
from django.db.models import Q
from django import forms

from isisdata.models import *
from zotero.models import ImportAccession
from isisdata.helper_methods import strip_punctuation
import six, iso8601
from unidecode import unidecode
from curation.tracking import TrackingWorkflow
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


# class ChoiceMethodFilter(django_filters.MethodFilter, django_filters.ChoiceFilter):
#     pass





class CitationFilter(django_filters.FilterSet):
    strict = STRICTNESS.RETURN_NO_RESULTS
    # strict = STRICTNESS.RAISE_VALIDATION_ERROR

    # id = django_filters.MethodFilter(name='id', lookup_type='exact')
    id = django_filters.CharFilter(method='filter_id')
    # title = django_filters.MethodFilter(name='title', lookup_type='icontains')
    title = django_filters.CharFilter(method='filter_title')
    type_controlled = django_filters.ChoiceFilter(choices=[('', 'All')] + list(Citation.TYPE_CHOICES))
    # publication_date_from = django_filters.MethodFilter()
    publication_date_from = django_filters.CharFilter(method='filter_publication_date_from')
    # publication_date_to = django_filters.MethodFilter()
    publication_date_to = django_filters.CharFilter(method='filter_publication_date_to')
    # abstract = django_filters.MethodFilter(name='abstract', lookup_type='icontains')
    abstract = django_filters.CharFilter(method='filter_abstract')
    # description = django_filters.MethodFilter(name='description', lookup_type='icontains')
    description = django_filters.CharFilter(method='filter_description')

    # author_or_editor = django_filters.MethodFilter()
    author_or_editor = django_filters.CharFilter(method='filter_author_or_editor')
    # periodical = django_filters.MethodFilter()
    periodical = django_filters.CharFilter(method='filter_periodical')
    # publisher = django_filters.MethodFilter()
    publisher = django_filters.CharFilter(method='filter_publisher')
    # subject = django_filters.MethodFilter()
    subject = django_filters.CharFilter(method='filter_subject')

    record_status = django_filters.ChoiceFilter(name='record_status_value', choices=[('', 'All')] + list(CuratedMixin.STATUS_CHOICES))
    in_collections = django_filters.CharFilter(method='filter_in_collections', widget=forms.HiddenInput())
    zotero_accession = django_filters.CharFilter(widget=forms.HiddenInput())
    belongs_to = django_filters.CharFilter(widget=forms.HiddenInput())

    tracking_state = django_filters.ChoiceFilter(choices=[('', 'All')] + list(Citation.TRACKING_CHOICES), method='filter_tracking_state')

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
                    self.zotero_accession_date = accession.imported_on
            except ImportAccession.DoesNotExist:
                self.zotero_accession_name = "Zotero accession could not be found."

        dataset = self.data.get('belongs_to', None)
        if dataset:
            try:
                ds = Dataset.objects.get(pk=dataset)
                if ds:
                    self.dataset_name = ds.name
            except Dataset.DoesNotExist:
                self.dataset_name = "Dataset could not be found."

    class Meta:
        model = Citation
        fields = [
            'id', 'title', 'abstract', 'description',
            'publication_date_from', 'publication_date_to',
            'author_or_editor', 'periodical', 'record_status',
            'belongs_to', 'zotero_accession', 'in_collections',
            'tracking_state'
        ]
        # order_by = [
        #     ('publication_date', 'Publication date (ascending)'),
        #     ('-publication_date', 'Publication date (descending)'),
        #     ('title_for_sort', 'Title (ascending)'),
        #     ('-title_for_sort', 'Title (descending)')
        # ]
    o = filters.OrderingFilter(
        # tuple-mapping retains order
        fields=(
            ('publication_date', 'publication_date'),
            ('title', 'title_for_sort'),
            ('part_details__page_begin', 'start_page'),
            ('modified_on', 'modified')
        ),

        # labels do not need to retain order
        field_labels={
            'publication_date': 'Publication date',
            'title': 'Title',
            'start_page': 'Start page',
            'modified': 'Last modified'
        }
    )

    # def get_ordering_field(self):
    #     if self._meta.order_by:
    #         if isinstance(self._meta.order_by, (list, tuple)):
    #             if isinstance(self._meta.order_by[0], (list, tuple)):
    #                 # e.g. (('field', 'Display name'), ...)
    #                 choices = [(f[0], f[1]) for f in self._meta.order_by]
    #             else:
    #                 choices = []
    #                 for f in self._meta.order_by:
    #                     if f[0] == '-':
    #                         label = _('%s (descending)' % capfirst(f[1:]))
    #                     else:
    #                         label = capfirst(f)
    #                     choices.append((f, label))
    #         else:
    #             # add asc and desc field names
    #             # use the filter's label if provided
    #             choices = []
    #             for f, fltr in self.filters.items():
    #                 choices.extend([
    #                     (f, fltr.label or capfirst(f)),
    #                     ("-%s" % (f), _('%s (descending)' % (fltr.label or capfirst(f))))
    #                 ])
    #         return forms.ChoiceField(widget=forms.HiddenInput(attrs={'value':"publication_date"}), choices=choices, initial="publication_date")

    def filter_id(self, queryset, name, value):
        if not value:
            return queryset

        ids = [i.strip() for i in value.split(',')]
        queryset = queryset.filter(pk__in=ids)
        return queryset

    def filter_title(self, queryset, name, value):
        value = unidecode(value)
        if not value:
            return queryset
        for part in value.split():
            queryset = queryset.filter(title_for_sort__icontains=part)
        return queryset

    def filter_abstract(self, queryset, name, value):
        if not value:
            return queryset
        for part in value.split():
            queryset = queryset.filter(abstract__icontains=part)
        return queryset

    def filter_description(self, queryset, name, value):
        if not value:
            return queryset
        for part in value.split():
            queryset = queryset.filter(description__icontains=part)
        return queryset

    def filter_publication_date_from(self, queryset, name, value):
        try:
            date = iso8601.parse_date(value)
        except:
            return queryset
        return queryset.filter(publication_date__gte=date)

    def filter_publication_date_to(self, queryset, name, value):
        try:
            date = iso8601.parse_date(value)
        except:
            return queryset
        return queryset.filter(publication_date__lte=date)

    def filter_author_or_editor(self, queryset, name, value):
        if not value:
            return queryset
        for part in value.split():
            queryset = queryset.filter(
                        acrelation__authority__name__icontains=part,
                        acrelation__type_controlled__in=[
                                    ACRelation.AUTHOR,
                                    ACRelation.EDITOR])
        return queryset

    def filter_periodical(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(acrelation__authority__name__icontains=value,
                               acrelation__type_controlled__in=[
                                    ACRelation.PERIODICAL,
                                    ACRelation.BOOK_SERIES])

    def filter_publisher(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(acrelation__authority__name__icontains=value,
                               acrelation__type_controlled=ACRelation.PUBLISHER)

    def filter_subject(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(acrelation__authority__name__icontains=value,
                               acrelation__type_controlled=ACRelation.SUBJECT)

    def filter_tracking_state(self, queryset, field, value):
        if not value:
            return queryset

        return queryset.filter(tracking_state=value)

    def filter_in_collections(self, queryset, field, value):
        if not value:
            return queryset
        q = Q()
        for collection in value:
            q |= Q(in_collections=collection)


        return queryset.filter(q)


class AuthorityFilter(django_filters.FilterSet):
    strict = STRICTNESS.RAISE_VALIDATION_ERROR # RETURN_NO_RESULTS

    id = django_filters.CharFilter(name='id', lookup_expr='exact')
    # name = django_filters.MethodFilter()
    name = django_filters.CharFilter(method='filter_name')
    type_controlled = django_filters.ChoiceFilter(choices=[('', 'All')] + list(Authority.TYPE_CHOICES))
    description = django_filters.CharFilter(name='description', lookup_expr='icontains')
    classification_system = django_filters.ChoiceFilter(name='classification_system', choices=[('', 'All')] + list(Authority.CLASS_SYSTEM_CHOICES))
    classification_code = django_filters.AllValuesFilter(name='classification_code')
    classification_hierarchy = django_filters.AllValuesFilter(name='classification_hierarchy')
    # linked_data = django_filters.MethodFilter()
    linked_data = django_filters.CharFilter(method='filter_linked_data')

    record_status_value = django_filters.ChoiceFilter(name='record_status_value', choices=[('', 'All')] + list(CuratedMixin.STATUS_CHOICES))

    datasets = Dataset.objects.all()
    dataset_list = [(ds.pk, ds.name) for ds in datasets ]
    belongs_to = django_filters.ChoiceFilter(choices=[('', 'All')] + dataset_list)

    tracking_state = django_filters.ChoiceFilter(choices=[('', 'All')] + list(Authority.TRACKING_CHOICES), method='filter_tracking_state')

    class Meta:
        model = Authority
        fields = [
            'id', 'name', 'type_controlled', 'description',
            'classification_system', 'classification_code',
            'classification_hierarchy', 'zotero_accession',
            'belongs_to', 'tracking_state']

        # order_by = [
        #     ('', 'None'),
        #     ('name_for_sort', 'Name (ascending)'),
        #     ('-name_for_sort', 'Name (descending)')
        # ]

    o = filters.OrderingFilter(
        # tuple-mapping retains order
        fields=(
            ('name', 'name_for_sort'),
        ),

        # labels do not need to retain order
        field_labels={
            'name': 'Name'
        }
    )

    def filter_tracking_state(self, queryset, field, value):
        if not value:
            return queryset

        return queryset.filter(tracking_state=value)

    def filter_name(self, queryset, name, value):
        value = unidecode(value)
        if not value:
            return queryset
        for part in value.split():
            queryset = queryset.filter(name_for_sort__icontains=part)

        return queryset

    def filter_linked_data(self, queryset, name, value):
        if not value:
            return queryset
        authority_ids = LinkedData.objects\
                            .filter(universal_resource_name__contains=value)\
                            .values_list('authorities__id', flat=True)\
                            .distinct()

        if len(authority_ids) == 1 and authority_ids[0] is None:
            return queryset.none()
        return queryset.filter(pk__in=authority_ids)
