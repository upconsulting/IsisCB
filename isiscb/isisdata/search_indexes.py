import datetime
from haystack import indexes
from haystack.constants import DEFAULT_OPERATOR, DJANGO_CT, DJANGO_ID, FUZZY_MAX_EXPANSIONS, FUZZY_MIN_SIM, ID
from django.forms import MultiValueField
from django.db.models import Prefetch
from isisdata.models import Citation, Authority
from isisdata.templatetags.app_filters import *
from isisdata.utils import normalize

import bleach
import unidecode
import unicodedata
from itertools import groupby
import time


class CitationIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(null=True, indexed=False, stored=True)
    book_title = indexes.CharField(null=True, stored=True)
    title_for_sort = indexes.CharField(null=True, indexed=False, stored=True)
    description = indexes.CharField(indexed=False, null=True)
    public = indexes.BooleanField(faceted=True, indexed=False)

    type = indexes.CharField(indexed=False, null=True)
    publication_date = indexes.MultiValueField(faceted=True, indexed=False,)
    publication_date_for_sort = indexes.CharField(null=True, indexed=False, stored=True)

    abstract = indexes.CharField(null=True, indexed=False)
    edition_details = indexes.CharField(null=True, indexed=False)
    physical_details = indexes.CharField(null=True, indexed=False)
    attributes = indexes.MultiValueField()
    authorities = indexes.MultiValueField(faceted=True, indexed=False)
    authors = indexes.MultiValueField(faceted=True, indexed=False)
    author_for_sort = indexes.CharField(null=True, indexed=False, stored=True)

    page_string = indexes.CharField(null=True, stored=True)

    # # Fields for COinS metadata.
    # # TODO: Populate these fields with values.
    # volume = indexes.CharField(null=True, stored=True)
    # issue = indexes.CharField(null=True, stored=True)
    # issn = indexes.CharField(null=True, stored=True)
    # doi = indexes.CharField(null=True, stored=True)
    #
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
    #
    # # TODO: fix typo (missing 'c' in 'serial_publications').
    serial_publications = indexes.MultiValueField(faceted=True, indexed=False)
    classification_terms = indexes.MultiValueField(faceted=True, indexed=False)
    concepts = indexes.MultiValueField(faceted=True, indexed=False)
    creative_works = indexes.MultiValueField(faceted=True, indexed=False)
    events = indexes.MultiValueField(faceted=True, indexed=False)

    all_contributor_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)
    #
    # # the following fields are for searching by author, contributor, etc.
    author_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    editor_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    advisor_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    contributor_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    translator_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    subject_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)
    category_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)
    publisher_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    school_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    institution_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    meeting_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    periodical_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    book_series_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    time_period_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)
    geographic_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)

    about_person_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    other_person_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)


    data_fields = [
        'id',
        'title',
        'description',
        'public',
        'type_controlled',
        'publication_date',
        'abstract',
        'edition_details',
        'physical_details',
        'attributes__id',
        'attributes__type_controlled__name',
        'attributes__value_freeform',
        'attributes__public',
        'acrelation__id',
        'acrelation__authority__public',
        'acrelation__authority__id',
        'acrelation__authority__name',
        'acrelation__authority__type_controlled',
        'acrelation__type_controlled',
        'acrelation__type_broad_controlled',
        'acrelation__data_display_order',
        'acrelation__name_for_display_in_citation',
        'part_details__page_begin',
        'part_details__page_end',
        'relations_to__id',
        'relations_to__type_controlled',
        'relations_to__subject__title',
        'relations_from__id',
        'relations_from__type_controlled',
        'relations_from__object__title',
    ]

    def get_model(self):
        return Citation

    def build_queryset(self, **kwargs):
        return Citation.objects.filter(public=True)

    def preprocess_queryset(self, qs):
        start = time.time()
        qs = groupby(qs.values(*self.data_fields), lambda r: r['id'])
        print 'preprocess', time.time() - start
        return qs

    def prepare(self, obj):
        """
        Fetches and adds/alters data before indexing.
        """

        identifier, data = obj      # groupby yields keys and iterators.

        # We need to able to __getitem__, below.
        data = list(data)
        self.prepared_data = {
            ID: identifier,
            DJANGO_CT: 'isisdata.citation',
            DJANGO_ID: unicode(identifier),
        }

        start = time.time()
        data_organized = {
            'id': identifier,
            'title': data[0]['title'],
            'description': data[0]['description'],
            'public': data[0]['public'],
            'type_controlled': data[0]['type_controlled'],
            'publication_date': data[0]['publication_date'],
            'abstract': data[0]['abstract'],
            'edition_details': data[0]['edition_details'],
            'physical_details': data[0]['physical_details'],
            'part_details': {
                'page_begin': data[0]['part_details__page_begin'],
                'page_end': data[0]['part_details__page_end'],
            },
            'attributes': [],
            'acrelations': [],
            'ccrelations_from': [],
            'ccrelations_to': [],
        }
        for row in data:
            if row['attributes__id']:
                data_organized['attributes'].append(row)
            if row['acrelation__id']:
                data_organized['acrelations'].append(row)
            if row['relations_from__id']:
                data_organized['ccrelations_from'].append(row)
            if row['relations_to__id']:
                data_organized['ccrelations_to'].append(row)
        # print 'sort', time.time() - start

        start = time.time()
        for field_name, field in self.fields.items():
            # Use the possibly overridden name, which will default to the
            # variable name of the field.
            # self.prepared_data[field.index_fieldname] = field.prepare(data_organized)

            if hasattr(self, "prepare_%s" % field_name):
                value = getattr(self, "prepare_%s" % field_name)(data_organized)
                self.prepared_data[field.index_fieldname] = value

            exact_field = "prepare_%s_exact" % field_name
            if hasattr(self, exact_field):
                self.prepared_data[exact_field] = getattr(self, exact_field)(data_organized)

        # print 'prepare', time.time() - start
        return self.prepared_data

    def _get_reviewed_book(self, data):
        """
        Attempt to retrieve the title of the work reviewed by the current
        :class:`.Citation` instance.
        """

        # The review - reviewed CCRelation may go in either direction.
        for ccrelation in data['ccrelations_from']:
            if ccrelation['relations_from__type_controlled'] == CCRelation.REVIEW_OF:
                return ccrelation['relations_from__object__title']

        # If we're still here, it means that there is no posessive CCRelation
        #  from this Citation; so we check the opposite direction.
        for ccrelation in data['ccrelations_to']:
            if ccrelation['relations_to__type_controlled'] == CCRelation.REVIEWED_BY:
                return ccrelation['relations_to__subject__title']

        return None

    def prepare_title(self, data):
        """
        Reviews are renamed to include the name of the reviewed work.
        """
        if data['type_controlled'] != 'RE':
            if not data['title']:
                return u"Title missing"
            return data['title']

        book = self._get_reviewed_book(data)

        if book == None:
            return u"Review of unknown publication"
        return u'Review of "' + book + u'"'

    def prepare_book_title(self, data):
        """
        If :class:`.Citation` is a chapter, keep track of the book to which it
        belongs.
        """
        if data['type_controlled'] == Citation.CHAPTER:
            for ccrelation in data['ccrelations_to']:
                if ccrelation['relations_to__type_controlled'] == CCRelation.INCLUDES_CHAPTER:
                    # we assume there is just one
                    return ccrelation['relations_to__subject__title']
        return None

    def prepare_title_for_sort(self, data):
        """
        We want to ignore non-ASCII characters when sorting, and group reviews
        together with the works that they review.
        """
        if data['type_controlled'] != Citation.REVIEW:
            if not data['title']:
                return u""
            return normalize(data['title'])

        book = self._get_reviewed_book(data)
        if book is None:
            return u""
        return normalize(book)

    def prepare_description(self, data):
        return data['description']

    def prepare_public(self, data):
        return data['public']

    def prepare_public_exact(self, data):
        return self.prepare_public(data)

    def prepare_type(self, data):
        """
        Use the display representation of Citation.type_controlled.
        """
        return dict(Citation.TYPE_CHOICES).get(data['type_controlled'])

    def prepare_publication_date(self, data):
        attributes = data.get('attributes', None)
        return [attr['attributes__value_freeform'] for attr in attributes
                if attr['attributes__type_controlled__name'] == 'PublicationDate']

    def prepare_publication_date_exact(self, data):
        return self.prepare_publication_date(data)

    def prepare_publication_date_for_sort(self, data):
        """
        If Citation.publication_data is not pre-filled, retrieve it from the
        formal Attribute (if possible).
        """

        if data['publication_date']:
            return data['publication_date']

        for attribute in data['attributes']:
            if attribute['attributes__type_controlled__name'] == 'PublicationDate':
                return attribute['attributes__value_freeform']
        return ''

    def prepare_abstract(self, data):
        return data['abstract']

    def prepare_edition_details(self, data):
        return data['edition_details']

    def prepare_physical_details(self, data):
        return data['physical_details']

    def prepare_attributes(self, data):
        return [a['attributes__value_freeform'] for a in data['attributes']
                if a['attributes__public']]

    def prepare_authorities(self, data):
        return [a['acrelation__authority__name'] for a in data['acrelations']
                if a['acrelation__authority__public']]

    def prepare_authorities_exact(self, data):
        return [a['acrelation__authority__id'] for a in data['acrelations']
                if a['acrelation__authority__public']]

    def _prepare_author_names(self, authors):
        names = []
        for author in authors:
            # Prefer the name as stored in the ACRelation, if present.
            name = author.get('acrelation__name_for_display_in_citation',
                              author['acrelation__authority__name'])
            names.append(name)
        return names

    def _get_all_contributors(self, data):
        authors = [a for a in data['acrelations']
                   if a['acrelation__type_broad_controlled'] == ACRelation.PERSONAL_RESPONS
                   and int(a['acrelation__data_display_order']) < 30]

        return sorted(authors, key=lambda a: a['acrelation__data_display_order'])

    def _prepare_authorities(self, data, getter, criterion):
        return [getter(a) for a in data['acrelations']
                if a['acrelation__authority__public'] and criterion(a)]

    def _authority_name_getter(self, datum):
        return datum['acrelation__authority__name'].strip()

    def _authority_id_getter(self, datum):
        return datum['acrelation__authority__id'].strip()

    def prepare_authors(self, data):
        """
        Raw names.
        """
        authors = self._get_all_contributors(data)
        return self._prepare_author_names(authors)

    def prepare_authors_exact(self, data):
        return self.prepare_authors(data)

    def prepare_author_for_sort(self, data):
        """
        Only the first author is used for sorting :class:`.Citation` search
        results.
        """
        names = self.prepare_authors(data)
        if len(names) == 0:
            return u""
        return names[0]

    def prepare_page_string(self, data):
        """
        This is here just so that we can sort chapters in books.
        """
        if data['type_controlled'] != Citation.CHAPTER:
            return ""
        page_start_string = data['part_details']['page_begin']
        page_end_string = data['part_details']['page_end']
        if page_start_string and page_end_string:
            return "pp. " + str(page_start_string) + "-" + str(page_end_string)
        if page_start_string:
            return "p. " + str(page_start_string)
        if page_end_string:
            return "p. " + str(page_end_string)
        return ""

    def prepare_subjects(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.SUBJECT and a['acrelation__authority__type_controlled'] not in [Authority.GEOGRAPHIC_TERM, Authority.TIME_PERIOD]
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_subjects_exact(self, data):
        return self.prepare_subjects(data)

    def prepare_persons(self, data):
        criterion = lambda a: a['acrelation__type_broad_controlled'] == ACRelation.PERSONAL_RESPONS
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_persons_exact(self, data):
        return self.prepare_persons(data)

    def prepare_categories(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.CATEGORY
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_categories_exact(self, data):
        return self.prepare_categories(data)

    def prepare_editors(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.EDITOR
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_editors_exact(self, data):
        return self.prepare_editors(data)

    def prepare_advisors(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.ADVISOR
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_advisors_exact(self, data):
        return self.prepare_advisors(data)

    def prepare_translators(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.TRANSLATOR
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_translators_exact(self, data):
        return self.prepare_translators(data)

    def prepare_publishers(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.PUBLISHER
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_publishers_exact(self, data):
        return self.prepare_publishers(data)

    def prepare_schools(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.SCHOOL
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_schools_exact(self, data):
        return self.prepare_schools(data)

    def prepare_institutions(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.INSTITUTION
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_institutions_exact(self, data):
        return self.prepare_institutions(data)

    def prepare_meetings(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.MEETING
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_meetings_exact(self, data):
        return self.prepare_meetings(data)

    def prepare_periodicals(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.PERIODICAL
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_periodicals_exact(self, data):
        return self.prepare_periodicals(data)

    def prepare_book_series(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.BOOK_SERIES
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_book_series_exact(self, data):
        return self.prepare_book_series(data)

    def prepare_time_periods(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.SUBJECT
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_time_periods_exact(self, data):
        return self.prepare_time_periods(data)

    def prepare_geographics(self, data):
        criterion = lambda a: a['acrelation__authority__type_controlled'] == Authority.GEOGRAPHIC_TERM and a['acrelation__type_controlled'] == ACRelation.SUBJECT
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_geographics_exact(self, data):
        return self.prepare_geographics(data)

    def prepare_people(self, data):
        criterion = lambda a: a['acrelation__authority__type_controlled'] == Authority.PERSON and a['acrelation__type_controlled'] == ACRelation.SUBJECT
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_people_exact(self, data):
        return self.prepare_people(data)

    def prepare_subject_institutions(self, data):
        criterion = lambda a: a['acrelation__authority__type_controlled'] == Authority.INSTITUTION and a['acrelation__type_controlled'] == ACRelation.SUBJECT
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_subject_institutions_exact(self, data):
        return self.prepare_subject_institutions(data)

    def prepare_serial_publications(self, data):
        criterion = lambda a: a['acrelation__authority__type_controlled']  == Authority.SERIAL_PUBLICATION and a['acrelation__type_controlled'] == ACRelation.SUBJECT
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_serial_publications_exact(self, data):
        return self.prepare_serial_publications(data)

    def prepare_classification_terms(self, data):
        criterion = lambda a: a['acrelation__authority__type_controlled']  == Authority.CLASSIFICATION_TERM and a['acrelation__type_controlled'] == ACRelation.SUBJECT
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_classification_terms_exact(self, data):
        return self.prepare_classification_terms(data)

    def prepare_concepts(self, data):
        criterion = lambda a: a['acrelation__authority__type_controlled']  == Authority.CONCEPT and a['acrelation__type_controlled'] == ACRelation.SUBJECT
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_concepts_exact(self, data):
        return self.prepare_concepts(data)

    def prepare_creative_works(self, data):
        criterion = lambda a: a['acrelation__authority__type_controlled']  == Authority.CREATIVE_WORK and a['acrelation__type_controlled'] == ACRelation.SUBJECT
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_creative_works_exact(self, data):
        return self.prepare_creative_works(data)

    def prepare_events(self, data):
        criterion = lambda a: a['acrelation__authority__type_controlled']  == Authority.EVENT and a['acrelation__type_controlled'] == ACRelation.SUBJECT
        return self._prepare_authorities(data, self._authority_name_getter, criterion)

    def prepare_events_exact(self, data):
        return self.prepare_events(data)

    def prepare_all_contributor_ids(self, data):
        authors = self._get_all_contributors(data)
        return [a['acrelation__authority__id'] for a in authors]

    def prepare_all_contributor_ids_exact(self, data):
        return self.prepare_all_contributor_ids(data)

    def prepare_author_ids(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.AUTHOR
        return self._prepare_authorities(data, self._authority_id_getter, criterion)

    def prepare_author_ids_exact(self, data):
        return self.prepare_author_ids(data)

    def prepare_editor_ids(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.EDITOR
        return self._prepare_authorities(data, self._authority_id_getter, criterion)

    def prepare_editor_ids_exact(self, data):
        return self.prepare_editor_ids(data)

    def prepare_advisor_ids(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.ADVISOR
        return self._prepare_authorities(data, self._authority_id_getter, criterion)

    def prepare_advisor_ids_exact(self, data):
        return self.prepare_advisor_ids(data)

    def prepare_contributor_ids(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.CONTRIBUTOR
        return self._prepare_authorities(data, self._authority_id_getter, criterion)

    def prepare_contributor_ids_exact(self, data):
        return self.prepare_contributor_ids(data)

    def prepare_translator_ids(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.TRANSLATOR
        return self._prepare_authorities(data, self._authority_id_getter, criterion)

    def prepare_translator_ids_exact(self, data):
        return self.prepare_translator_ids(data)

    def prepare_subject_ids(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.SUBJECT
        return self._prepare_authorities(data, self._authority_id_getter, criterion)

    def prepare_subject_ids_exact(self, data):
        return self.prepare_subject_ids(data)

    def prepare_category_ids(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.CATEGORY
        return self._prepare_authorities(data, self._authority_id_getter, criterion)

    def prepare_category_ids_exact(self, data):
        return self.prepare_category_ids(data)

    def prepare_publisher_ids(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.PUBLISHER
        return self._prepare_authorities(data, self._authority_id_getter, criterion)

    def prepare_publisher_ids_exact(self, data):
        return self.prepare_publisher_ids(data)

    def prepare_school_ids(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.SCHOOL
        return self._prepare_authorities(data, self._authority_id_getter, criterion)

    def prepare_school_ids_exact(self, data):
        return self.prepare_school_ids(data)

    def prepare_institution_ids(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.SUBJECT and a['acrelation__authority__type_controlled'] == Authority.INSTITUTION
        return self._prepare_authorities(data, self._authority_id_getter, criterion)

    def prepare_institution_ids_exact(self, data):
        return self.prepare_institution_ids(data)

    def prepare_meeting_ids(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.MEETING
        return self._prepare_authorities(data, self._authority_id_getter, criterion)

    def prepare_meeting_ids_exact(self, data):
        return self.prepare_meeting_ids(data)

    def prepare_periodical_ids(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.PERIODICAL
        return self._prepare_authorities(data, self._authority_id_getter, criterion)

    def prepare_periodical_ids_exact(self, data):
        return self.prepare_periodical_ids(data)

    def prepare_book_series_ids(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.BOOK_SERIES
        return self._prepare_authorities(data, self._authority_id_getter, criterion)

    def prepare_book_series_ids_exact(self, data):
        return self.prepare_book_series_ids(data)

    def prepare_time_period_ids(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.SUBJECT and a['acrelation__authority__type_controlled'] == Authority.TIME_PERIOD
        return self._prepare_authorities(data, self._authority_id_getter, criterion)

    def prepare_time_period_ids_exact(self, data):
        return self.prepare_time_period_ids(data)

    def prepare_geographic_ids(self, data):
        criterion = lambda a: a['acrelation__type_controlled'] == ACRelation.SUBJECT and a['acrelation__authority__type_controlled'] == Authority.GEOGRAPHIC_TERM
        return self._prepare_authorities(data, self._authority_id_getter, criterion)

    def prepare_geographic_ids_exact(self, data):
        return self.prepare_geographic_ids(data)

    def prepare_about_person_ids(self, data):
        criterion = lambda a: a['acrelation__type_broad_controlled'] == ACRelation.SUBJECT_CONTENT
        return self._prepare_authorities(data, self._authority_id_getter, criterion)

    def prepare_about_person_ids_exact(self, data):
        return self.prepare_about_person_ids(data)

    def prepare_other_person_ids(self, data):
        criterion = lambda a: a['acrelation__type_broad_controlled'] in [ACRelation.INSTITUTIONAL_HOST, ACRelation.PUBLICATION_HOST, ACRelation.PERSONAL_RESPONS] and a['acrelation__type_controlled'] not in [ACRelation.AUTHOR, ACRelation.CONTRIBUTOR]
        return self._prepare_authorities(data, self._authority_id_getter, criterion)

    def prepare_other_person_ids_exact(self, data):
        return self.prepare_other_person_ids(data)


class AuthorityIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name', indexed=False)
    description = indexes.CharField(model_attr='description', null=True, indexed=False)
    attributes = indexes.MultiValueField(indexed=False)
    authority_type = indexes.CharField(model_attr='type_controlled', indexed=False, null=True)
    public = indexes.BooleanField(model_attr='public', faceted=True, indexed=False)
    dates = indexes.MultiValueField(indexed=False)
    #citation_nr = indexes.CharField(indexed=False)

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

    #def prepare_citation_nr(self, obj):
        #ACRelation.objects.filter(authority=obj, citation__public=True).distinct('citation_id').count()
