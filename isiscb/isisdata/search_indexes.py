import datetime
from haystack import indexes
from django.forms import MultiValueField
from django.db.models import Prefetch
from isisdata.models import Citation, Authority
from isisdata.templatetags.app_filters import *

import bleach
import unidecode
import unicodedata


def remove_control_characters(s):
    s = unicode(s)
    return u"".join(ch for ch in s if unicodedata.category(ch)[0]!="C")


class CitationIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(model_attr='title', null=True, indexed=False, stored=True)
    book_title = indexes.CharField(null=True, stored=True)
    title_for_sort = indexes.CharField(null=True, indexed=False, stored=True)
    description = indexes.CharField(model_attr='description',indexed=False, null=True)
    public = indexes.BooleanField(model_attr='public', faceted=True, indexed=False)

    type = indexes.CharField(model_attr='type_controlled', indexed=False, null=True)
    publication_date = indexes.MultiValueField(faceted=True, indexed=False,)
    publication_date_for_sort = indexes.CharField(null=True, indexed=False, stored=True)

    abstract = indexes.CharField(model_attr='abstract', null=True, indexed=False)
    edition_details = indexes.CharField(model_attr='edition_details', null=True, indexed=False)
    physical_details = indexes.CharField(model_attr='physical_details', null=True, indexed=False)
    attributes = indexes.MultiValueField()
    authorities = indexes.MultiValueField(faceted=True, indexed=False)
    authors = indexes.MultiValueField(faceted=True, indexed=False)
    author_for_sort = indexes.CharField(null=True, indexed=False, stored=True)

    page_string = indexes.CharField(null=True, stored=True)

    subjects = indexes.MultiValueField(faceted=True, indexed=False)
    persons = indexes.MultiValueField(faceted=True, indexed=False)
    categories = indexes.MultiValueField(faceted=True, indexed=False)
    editors = indexes.MultiValueField(faceted=True, indexed=False)
    advisors = indexes.MultiValueField(faceted=True, indexed=False)
    translators = indexes.MultiValueField(faceted=True, indexed=False)
    publishers = indexes.MultiValueField(faceted=True, indexed=False)
    schools = indexes.MultiValueField(faceted=True, indexed=False)
    institutions = indexes.MultiValueField(faceted=True, indexed=False)
    meetings = indexes.MultiValueField(faceted=True, indexed=False)
    periodicals = indexes.MultiValueField(faceted=True, indexed=False)
    book_series = indexes.MultiValueField(faceted=True, indexed=False)
    time_periods = indexes.MultiValueField(faceted=True, indexed=False)
    geographics = indexes.MultiValueField(faceted=True, indexed=False)
    people = indexes.MultiValueField(faceted=True, indexed=False)
    subject_institutions = indexes.MultiValueField(faceted=True, indexed=False)
    serial_publiations = indexes.MultiValueField(faceted=True, indexed=False)
    classification_terms = indexes.MultiValueField(faceted=True, indexed=False)
    concepts = indexes.MultiValueField(faceted=True, indexed=False)
    creative_works = indexes.MultiValueField(faceted=True, indexed=False)
    events = indexes.MultiValueField(faceted=True, indexed=False)

    # the following fields are for searching by author, contributor, etc.
    author_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    editor_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    advisor_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    contributor_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    translator_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    subject_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    category_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    publisher_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    school_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    institution_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    meeting_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    periodical_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    book_series_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)

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
        return self.get_model().objects.filter(public=True)

    def prepare(self, obj):
        """
        Coerce all unicode values to ASCII bytestrings, to avoid characters
        that make haystack choke.
        """
        self.prepared_data = super(CitationIndex, self).prepare(obj)

        for k, v in self.prepared_data.iteritems():
            if type(v) in [unicode, str]:
                self.prepared_data[k] = remove_control_characters(v.strip())
                # self.prepared_data[k] = unidecode.unidecode(remove_control_characters(v)).strip()
        return self.prepared_data

    def prepare_type(self, obj):
        return obj.get_type_controlled_display()

    def prepare_title(self, obj):
        if not obj.type_controlled == 'RE':
            if not obj.title:
                return "Title missing"
            return obj.title

        book = self.get_reviewed_book(obj)

        if book == None:
            return "Review of unknown publication"

        return 'Review of "' + book.title + '"'

    def prepare_title_for_sort(self, obj):
        if not obj.type_controlled == 'RE':
            return obj.normalized_title

        book = self.get_reviewed_book(obj)
        if not book:
            return ''

        return book.normalized_title


    def get_reviewed_book(self, obj):
        # if citation is a review build title from reviewed citation
        reviewed_books = CCRelation.objects.filter(subject_id=obj.id, type_controlled='RO')

        # sometimes RO relationship is not specified then use inverse reviewed by
        book = None
        if not reviewed_books:
            reviewed_books = CCRelation.objects.filter(object_id=obj.id, type_controlled='RB')
            if reviewed_books:
                book = reviewed_books[0].subject
        else:
            book = reviewed_books[0].object

        return book

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
        return name

    def prepare_page_string(self, obj):
        if obj.type_controlled != Citation.CHAPTER:
            return ""
        page_start_string = obj.part_details.page_begin
        page_end_string = obj.part_details.page_end
        if page_start_string and page_end_string:
            return "pp. " + str(page_start_string) + "-" + str(page_end_string)
        if page_start_string:
            return "p. " + str(page_start_string)
        if page_end_string:
            return "p. " + str(page_end_string)
        return ""

    def prepare_book_title(self, obj):
        if obj.type_controlled in ['CH']:
            parent_relation = CCRelation.objects.filter(object_id=obj.id, type_controlled='IC')
            # we assume there is just one
            if parent_relation:
                return parent_relation[0].subject.title
        return None

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
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['AU'])]

    def prepare_editor_ids(self, obj):
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['ED'])]

    def prepare_advisor_ids(self, obj):
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['AD'])]

    def prepare_contributor_ids(self, obj):
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['CO'])]

    def prepare_translator_ids(self, obj):
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['TR'])]

    def prepare_subject_ids(self, obj):
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['SU'])]

    def prepare_category_ids(self, obj):
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['CA'])]

    def prepare_publisher_ids(self, obj):
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['PU'])]

    def prepare_school_ids(self, obj):
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['SC'])]

    def prepare_institution_ids(self, obj):
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['IN'])]

    def prepare_meeting_ids(self, obj):
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['ME'])]

    def prepare_periodical_ids(self, obj):
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['PE'])]

    def prepare_book_series_ids(self, obj):
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(type_controlled__in=['BS'])]

    def prepare_about_person_ids(self, obj):
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(type_broad_controlled='SC')]

    def prepare_other_person_ids(self, obj):
        query = Q(type_broad_controlled__in=['IH', 'PH', 'PR']) & ~Q(type_controlled__in=['AU','CO'])
        return [acrel.authority.id for acrel in obj.acrelation_set.filter(public=True).filter(query)]


class AuthorityIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name', indexed=False)
    description = indexes.CharField(model_attr='description', null=True, indexed=False)
    attributes = indexes.MultiValueField(indexed=False)
    authority_type = indexes.CharField(model_attr='type_controlled', indexed=False, null=True)
    public = indexes.BooleanField(model_attr='public', faceted=True, indexed=False)
    dates = indexes.MultiValueField(indexed=False)

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

    def prepare(self, obj):
        """
        Coerce all unicode values to ASCII bytestrings, to avoid characters
        that make haystack choke.
        """
        self.prepared_data = super(AuthorityIndex, self).prepare(obj)

        for k, v in self.prepared_data.iteritems():
            if type(v) is unicode:
                self.prepared_data[k] = remove_control_characters(v.strip())
        return self.prepared_data

    def prepare_attributes(self, obj):
        return [attr.value_freeform for attr
                in obj.attributes.filter(public=True)]

    def prepare_authority_type(self, obj):
        return obj.get_type_controlled_display()


    def prepare_xtype(self, obj):
        return obj.get_type_controlled_display()

    def prepare_dates(self, obj):
        return [date.value_freeform for date in obj.attributes.filter(type_controlled__value_content_type__model__in=['datevalue', 'datetimevalue'])]
