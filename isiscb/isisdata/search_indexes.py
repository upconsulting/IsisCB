import datetime
from haystack import indexes
from django.forms import MultiValueField
from django.db.models import Prefetch
from isisdata.models import Citation, Authority
from isisdata.templatetags.app_filters import *

import bleach


class CitationIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(model_attr='title', null=True, indexed=False, stored=True)
    title_for_sort = indexes.CharField(null=True, indexed=False, stored=True)
    description = indexes.CharField(model_attr='description', null=True)
    public = indexes.BooleanField(model_attr='public', faceted=True, indexed=False)

    type = indexes.CharField(model_attr='type_controlled', indexed=False, null=True)
    publication_date = indexes.MultiValueField(faceted=True)
    publication_date_for_sort = indexes.CharField(null=True, indexed=False, stored=True)

    abstract = indexes.CharField(model_attr='abstract', null=True)
    edition_details = indexes.CharField(model_attr='edition_details', null=True)
    physical_details = indexes.CharField(model_attr='physical_details', null=True)
    attributes = indexes.MultiValueField()
    authorities = indexes.MultiValueField(faceted=True)
    authors = indexes.MultiValueField(faceted=True)
    author_for_sort = indexes.CharField(null=True, indexed=False, stored=True)

    subjects = indexes.MultiValueField(faceted=True)
    persons = indexes.MultiValueField(faceted=True)
    categories = indexes.MultiValueField(faceted=True)
    editors = indexes.MultiValueField(faceted=True)
    advisors = indexes.MultiValueField(faceted=True)
    translators = indexes.MultiValueField(faceted=True)
    publishers = indexes.MultiValueField(faceted=True)
    schools = indexes.MultiValueField(faceted=True)
    institutions = indexes.MultiValueField(faceted=True)
    meetings = indexes.MultiValueField(faceted=True)
    periodicals = indexes.MultiValueField(faceted=True)
    book_series = indexes.MultiValueField(faceted=True)
    time_periods = indexes.MultiValueField(faceted=True)
    geographics = indexes.MultiValueField(faceted=True)
    people = indexes.MultiValueField(faceted=True)
    subject_institutions = indexes.MultiValueField(faceted=True)
    serial_publiations = indexes.MultiValueField(faceted=True)
    classification_terms = indexes.MultiValueField(faceted=True)
    concepts = indexes.MultiValueField(faceted=True)
    creative_works = indexes.MultiValueField(faceted=True)
    events = indexes.MultiValueField(faceted=True)

    # the following fields are for searching by author, contributor, etc.
    author_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    about_person_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    other_person_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)

    def get_model(self):
        return Citation

    def load_all_queryset(self):
        """
        Add pre-loading of related fields using select_related and
        prefetch_related.
        """
        return Citation.objects.all().select_related(
                'acrelation_set__authority__name',
                'acrelation_set__authority__type_controlled',
                'acrelation_set__type_controlled'
            ).prefetch_related(
                Prefetch("attributes",
                         queryset=AttributeType.objects.select_related(
                            "type_controlled__name",
                            "value_freeform"))
            )

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.all()

    def prepare_type(self, obj):
        return obj.get_type_controlled_display()

    def prepare_title_for_sort(self, obj):
        return obj.normalized_title

    def prepare_publication_date(self, obj):
        return [date.value_freeform for date in obj.attributes.filter(type_controlled__name='PublicationDate')]

    def prepare_publication_date_for_sort(self, obj):
        if obj.publication_date:
            return obj.publication_date

        dates = obj.attributes.filter(type_controlled__name='PublicationDate')
        if not dates:
            return ''

        date = dates[0]
        if not date:
            return ''

        return date.value_freeform

    def prepare_authorities(self, obj):
        # Store a list of id's for filtering
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True)]

    def prepare_attributes(self, obj):
        return [attr.value_freeform for attr in obj.attributes.filter(public=True)]

    def prepare_authors(self, obj):
        #authors = obj.acrelation_set.filter(type_controlled__in=['AU', 'CO', 'ED'], data_display_order__lt=30).order_by('data_display_order')
        authors = obj.get_all_contributors
        names = []
        for author in authors:
            name = author.name_for_display_in_citation
            if not name:
                name = author.authority.name
            names.append(name)
        return names

    # TODO: this method needs to be changed to include author order
    def prepare_author_for_sort(self, obj):
        #editors = obj.acrelation_set.filter(type_controlled__in=['ED'])
        #if obj.type_controlled == 'BO' and editors:
        #    authors = obj.acrelation_set.filter(type_controlled__in=['ED'])
        #else:
        #    authors = obj.acrelation_set.filter(type_controlled__in=['AU'])
        #if not authors:
        #    return ''
        authors = obj.get_all_contributors
        if not authors:
            return ""
        author = authors[0]
        if not author:
            return ''

        name = author.name_for_display_in_citation
        if not name:
            name = author.authority.name
        return name;

    def prepare_subjects(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['SU']).exclude(authority__type_controlled__in=['GE', 'TI'])]

    def prepare_persons(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['PR'])]

    def prepare_categories(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['CA'])]

    def prepare_editors(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['ED'])]

    def prepare_advisors(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['AD'])]

    def prepare_translators(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['TR'])]

    def prepare_publishers(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['PU'])]

    def prepare_schools(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['SC'])]

    def prepare_institutions(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['IN'])]

    def prepare_meetings(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['ME'])]

    def prepare_periodicals(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['PE'])]

    def prepare_book_series(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['BS'])]

    def prepare_time_periods(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['SU'], authority__type_controlled__in=['TI'])]

    def prepare_geographics(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['SU'], authority__type_controlled__in=['GE'])]

    def prepare_people(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['SU'], authority__type_controlled__in=['PE'])]

    def prepare_subject_institutions(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['SU'], authority__type_controlled__in=['IN'])]

    def prepare_serial_publications(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['SU'], authority__type_controlled__in=['SE'])]

    def prepare_classification_terms(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['SU'], authority__type_controlled__in=['CT'])]

    def prepare_concepts(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['SU'], authority__type_controlled__in=['CO'])]

    def prepare_creative_works(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['SU'], authority__type_controlled__in=['CW'])]

    def prepare_events(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['SU'], authority__type_controlled__in=['EV'])]

    def prepare_author_ids(self, obj):
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['AU', 'CO'])]

    def prepare_about_person_ids(self, obj):
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(type_broad_controlled='SC')]

    def prepare_other_person_ids(self, obj):
        query = Q(type_broad_controlled__in=['IH', 'PH', 'PR']) & ~Q(type_controlled__in=['AU','CO'])
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(query)]


class AuthorityIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name')
    description = indexes.CharField(model_attr='description', null=True)
    attributes = indexes.MultiValueField()
    authority_type = indexes.CharField(model_attr='type_controlled', indexed=False, null=True)

    def get_model(self):
        return Authority

    def load_all_queryset(self):
        """
        Add pre-loading of related fields using select_related and
        prefetch_related.
        """
        return Authority.objects.all().prefetch_related(
                Prefetch("attributes",
                         queryset=AttributeType.objects.select_related(
                            "value_freeform"))
            )

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.filter(public=True)

    def prepare_attributes(self, obj):
        return [attr.value_freeform for attr
                in obj.attributes.filter(public=True)]

    def prepare_authority_type(self, obj):
        return obj.get_type_controlled_display()

    def prepare_xtype(self, obj):
        return obj.get_type_controlled_display()
