from __future__ import print_function
from __future__ import unicode_literals
from builtins import str
import datetime
from haystack import indexes
from haystack.constants import DEFAULT_OPERATOR, DJANGO_CT, DJANGO_ID, FUZZY_MAX_EXPANSIONS, FUZZY_MIN_SIM, ID
from django.forms import MultiValueField
from django.db.models import Prefetch
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from isisdata.models import Citation, Authority
from isisdata.templatetags.app_filters import *
from isisdata.utils import normalize

import bleach
import unidecode
import unicodedata
import re
from itertools import groupby
import time
from collections import defaultdict


class CitationIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True)
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
    author_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    all_contributor_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)
    contributor_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    persons = indexes.MultiValueField(faceted=True, indexed=False)
    persons_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)

    editors = indexes.MultiValueField(faceted=True, indexed=False)
    editor_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)

    subjects = indexes.MultiValueField(faceted=True, indexed=False)
    subject_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)

    page_string = indexes.CharField(null=True, stored=True)

    complete_citation = indexes.CharField(null=True, indexed=True)
    stub_record_status = indexes.CharField(indexed=False, null=True, faceted=True)

    # # Fields for COinS metadata.
    # # TODO: Populate these fields with values.
    # volume = indexes.CharField(null=True, stored=True)
    # issue = indexes.CharField(null=True, stored=True)
    # issn = indexes.CharField(null=True, stored=True)
    # doi = indexes.CharField(null=True, stored=True)
    #

    institutions = indexes.MultiValueField(faceted=True, indexed=False)
    institution_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    subject_institutions = indexes.MultiValueField(faceted=True, indexed=False)

    categories = indexes.MultiValueField(faceted=True, indexed=False)
    category_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)

    advisors = indexes.MultiValueField(faceted=True, indexed=False)
    advisor_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)

    translators = indexes.MultiValueField(faceted=True, indexed=False)
    translator_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)

    publishers = indexes.MultiValueField(faceted=True, indexed=False)
    publisher_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)

    schools = indexes.MultiValueField(faceted=True, indexed=False)
    school_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)

    meetings = indexes.MultiValueField(faceted=True, indexed=False)
    meeting_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)

    periodicals = indexes.MultiValueField(faceted=True, indexed=False)
    periodical_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)

    book_series = indexes.MultiValueField(faceted=True, indexed=False)
    book_series_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)

    time_periods = indexes.MultiValueField(faceted=True, indexed=False)
    time_period_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)

    events = indexes.MultiValueField(faceted=True, indexed=False)
    event_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)

    events_timeperiods = indexes.MultiValueField(faceted=True, indexed=False)
    events_timeperiods_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)

    geographics = indexes.MultiValueField(faceted=True, indexed=False)
    geographic_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)
    geocodes = indexes.MultiValueField(faceted=True, indexed=False, null=True)

    cross_references = indexes.MultiValueField(faceted=True, indexed=False)
    cross_references_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)

    people = indexes.MultiValueField(faceted=True, indexed=False)
    about_person_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    other_person_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)

    serial_publications = indexes.MultiValueField(faceted=True, indexed=False)
    classification_terms = indexes.MultiValueField(faceted=True, indexed=False)
    concepts = indexes.MultiValueField(faceted=True, indexed=False)
    concepts_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)
    creative_works = indexes.MultiValueField(faceted=True, indexed=False)
    creative_works_ids = indexes.MultiValueField(faceted=False, indexed=False, null=True)

    # IEXP-21: for facet boxes on authority page
    concepts_by_subject_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)
    people_by_subject_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)
    institutions_by_subject_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)

    # IEXP-163
    concepts_only_by_subject_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)

    dataset_typed_names = indexes.MultiValueField(faceted=True, indexed=False)
    dataset_typed_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)

    dataset_names = indexes.MultiValueField(faceted=True, indexed=False)
    dataset_ids = indexes.MultiValueField(faceted=True, indexed=False, null=True)



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
        'belongs_to',
        'belongs_to__name',
        'complete_citation',
        'stub_record_status',
        'attributes__id',
        'attributes__type_controlled__name',
        'attributes__value_freeform',
        'attributes__value__attribute_id',
        'attributes__public',
        'acrelation__id',
        'acrelation__public',
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
        # return Citation.objects.filter(acrelation__authority__id='CBA000113906', public=True)    # Horse.
        return Citation.objects.filter(public=True)

    def preprocess_queryset(self, qs):
        return groupby(sorted(qs.values(*self.data_fields), key=lambda r: r['id']), lambda r: r['id'])

    def full_prepare(self, obj):
        self.prepared_data = self.prepare(obj)

        for field_name, field in list(self.fields.items()):
            # Duplicate data for faceted fields.
            if getattr(field, 'facet_for', None):
                source_field_name = self.fields[field.facet_for].index_fieldname

                # If there's data there, leave it alone. Otherwise, populate it
                # with whatever the related field has.
                if self.prepared_data.get(field_name, None) is None and source_field_name in self.prepared_data:
                    self.prepared_data[field.index_fieldname] = self.prepared_data[source_field_name]

            # Remove any fields that lack a value and are ``null=True``.
            if field.null is True:
                if self.prepared_data.get(field.index_fieldname, None) is None:
                    try:
                        del(self.prepared_data[field.index_fieldname])
                    except KeyError:    # It was never there....
                        pass

        return self.prepared_data

    def prepare(self, obj):
        """
        Fetches and adds/alters data before indexing.
        """
        if type(obj) is Citation:
            identifier = obj.id
            data = Citation.objects.filter(pk=obj.id).values(*self.data_fields)
        else:
            identifier, data = obj      # groupby yields keys and iterators.

        # We need to able to __getitem__, below.
        data = [row for row in data]
        self.prepared_data = {
            ID: identifier,
            DJANGO_CT: 'isisdata.citation',
            DJANGO_ID: str(identifier),
        }

        data_organized = {
            'id': identifier,
            'title': data[0]['title'],
            'description': data[0]['description'],
            'public': data[0]['public'],
            'type_controlled': data[0]['type_controlled'],
            'publication_date': data[0]['publication_date'],
            'abstract': data[0]['abstract'],
            'complete_citation': data[0]['complete_citation'],
            'stub_record_status': data[0]['stub_record_status'],
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

        self._index_belongs_to(data)

        start = time.time()
        for field_name, field in list(self.fields.items()):
            # Use the possibly overridden name, which will default to the
            # variable name of the field.
            # self.prepared_data[field.index_fieldname] = field.prepare(data_organized)
            if hasattr(self, "prepare_%s" % field_name):
                value = getattr(self, "prepare_%s" % field_name)(data_organized)
                self.prepared_data[field.index_fieldname] = value

            exact_field = "prepare_%s_exact" % field_name
            if hasattr(self, exact_field):
                self.prepared_data[exact_field] = getattr(self, exact_field)(data_organized)

        multivalue_data = defaultdict(list)
        for a in sorted(data_organized['acrelations'], key=lambda a: a['acrelation__data_display_order']):
            if not a['acrelation__public']:
                continue
            if a['acrelation__authority__id'] and not a['acrelation__authority__public']:
                continue

            if a['acrelation__authority__name']:
                name = remove_control_characters(a['acrelation__authority__name'].strip())
            elif a['acrelation__name_for_display_in_citation']:
                name = remove_control_characters(a['acrelation__name_for_display_in_citation'].strip())
            else:
                name = None

            try:
                ident = remove_control_characters(a['acrelation__authority__id'].strip())
            except AttributeError:
                ident = None

            multivalue_data['authorities'].append(name)
            if a['acrelation__type_controlled'] == ACRelation.SUBJECT:
                multivalue_data['subjects'].append(name)
                multivalue_data['subject_ids'].append(ident)

                if a['acrelation__authority__type_controlled'] == Authority.TIME_PERIOD:
                    multivalue_data['time_periods'].append(name)
                    multivalue_data['time_period_ids'].append(ident)
                    multivalue_data['events_timeperiods'].append(name)
                    multivalue_data['events_timeperiods_ids'].append(ident)
                elif a['acrelation__authority__type_controlled'] == Authority.GEOGRAPHIC_TERM:
                    multivalue_data['geographics'].append(name)
                    multivalue_data['geographic_ids'].append(ident)
                    authority = Authority.objects.get(pk=ident)
                    for attr in authority.attributes.all():
                        if attr.type_controlled.name == settings.COUNTRY_CODE_ATTRIBUTE:
                            country_codes = attr.value.display.split(",")
                            for code in country_codes:
                                multivalue_data['geocodes'].append(code.strip())
                else:
                    if a['acrelation__authority__type_controlled'] == Authority.INSTITUTION:
                        multivalue_data['subject_institutions'].append(name)
                        multivalue_data['institutions_by_subject_ids'].append(ident)
                    elif a['acrelation__authority__type_controlled'] == Authority.PERSON:
                        multivalue_data['people'].append(name)
                        multivalue_data['people_by_subject_ids'].append(ident)
                    elif a['acrelation__authority__type_controlled']  == Authority.SERIAL_PUBLICATION:
                        multivalue_data['serial_publications'].append(name)
                    elif a['acrelation__authority__type_controlled']  == Authority.CLASSIFICATION_TERM:
                        multivalue_data['classification_terms'].append(name)
                    elif a['acrelation__authority__type_controlled']  == Authority.CONCEPT:
                        multivalue_data['concepts'].append(name)
                        multivalue_data['concepts_by_subject_ids'].append(ident)
                        multivalue_data['concepts_only_by_subject_ids'].append(ident)
                    elif a['acrelation__authority__type_controlled']  == Authority.CREATIVE_WORK:
                        multivalue_data['creative_works'].append(name)
                        multivalue_data['concepts'].append(name)
                        multivalue_data['creative_works_ids'].append(ident)
                        multivalue_data['concepts_by_subject_ids'].append(ident)
                    elif a['acrelation__authority__type_controlled']  == Authority.EVENT:
                        multivalue_data['events'].append(name)
                        multivalue_data['events_ids'].append(ident)
                        multivalue_data['events_timeperiods'].append(name)
                        multivalue_data['events_timeperiods_ids'].append(ident)
                    elif a['acrelation__authority__type_controlled']  == Authority.CROSSREFERENCE:
                        multivalue_data['cross_references'].append(name)
                        multivalue_data['cross_references_ids'].append(ident)

            elif a['acrelation__type_controlled'] == ACRelation.INSTITUTION:
                multivalue_data['institutions'].append(name)
                multivalue_data['institution_ids'].append(ident)
            elif a['acrelation__type_controlled'] == ACRelation.CATEGORY:
                multivalue_data['categories'].append(name)
                multivalue_data['category_ids'].append(ident)
            elif a['acrelation__type_controlled'] == ACRelation.ADVISOR:
                multivalue_data['advisors'].append(name)
                multivalue_data['advisor_ids'].append(ident)
            elif a['acrelation__type_controlled'] == ACRelation.TRANSLATOR:
                multivalue_data['translators'].append(name)
                multivalue_data['translator_ids'].append(ident)
            elif a['acrelation__type_controlled'] == ACRelation.PUBLISHER:
                if name not in multivalue_data['publishers']:
                    multivalue_data['publishers'].append(name)
                if ident not in multivalue_data['publisher_ids']:
                    multivalue_data['publisher_ids'].append(ident)
            elif a['acrelation__type_controlled'] == ACRelation.SCHOOL:
                if name not in multivalue_data['schools']:
                    multivalue_data['schools'].append(name)
                if ident not in multivalue_data['school_ids']:
                    multivalue_data['school_ids'].append(ident)
            elif a['acrelation__type_controlled'] == ACRelation.MEETING:
                multivalue_data['meetings'].append(name)
                multivalue_data['meeting_ids'].append(ident)
            elif a['acrelation__type_controlled'] == ACRelation.PERIODICAL:
                multivalue_data['periodicals'].append(name)
                multivalue_data['periodical_ids'].append(ident)
            elif a['acrelation__type_controlled'] == ACRelation.BOOK_SERIES:
                multivalue_data['book_series'].append(name)
                multivalue_data['book_series_ids'].append(ident)
            elif a['acrelation__type_controlled'] == ACRelation.EDITOR:
                multivalue_data['editors'].append(name)
                multivalue_data['editor_ids'].append(ident)
            elif a['acrelation__type_controlled'] == ACRelation.CONTRIBUTOR:
                multivalue_data['contributor_ids'].append(ident)


            elif a['acrelation__type_broad_controlled'] == ACRelation.SUBJECT_CONTENT:
                multivalue_data['about_person_ids'].append(ident)

            if a['acrelation__type_broad_controlled'] in [ACRelation.INSTITUTIONAL_HOST, ACRelation.PUBLICATION_HOST, ACRelation.PERSONAL_RESPONS] and a['acrelation__type_controlled'] not in [ACRelation.AUTHOR, ACRelation.CONTRIBUTOR]:
                multivalue_data['other_person_ids'].append(ident)

            if a['acrelation__type_broad_controlled'] == ACRelation.PERSONAL_RESPONS:
                multivalue_data['persons'].append(name)
                multivalue_data['persons_ids'].append(ident)
                if int(a['acrelation__data_display_order']) < 30:
                    multivalue_data['all_contributor_ids'].append(ident)

                if a['acrelation__type_controlled'] == ACRelation.AUTHOR:
                    multivalue_data['author_ids'].append(ident)

                # Prefer the ACRelation.name_for_display_in_citation, if
                #  present.
                # IEXP-31: only append authors and editors to authors field
                if a['acrelation__type_controlled'] in [ACRelation.AUTHOR, ACRelation.EDITOR]:
                    aname = a['acrelation__name_for_display_in_citation']
                    if not aname:
                        aname = name
                    if aname not in multivalue_data['authors']:
                        multivalue_data['authors'].append(aname)

        if len(multivalue_data['authors']) > 0:
            self.prepared_data['author_for_sort'] = multivalue_data['authors'][0]
        else:
            self.prepared_data['author_for_sort'] = u""
        self.prepared_data.update(multivalue_data)

        return self.prepared_data

    def _index_belongs_to(self, data):
        if data[0]['belongs_to']:
            self.prepared_data['dataset_ids'] = data[0]['belongs_to']
        if data[0]['belongs_to__name']:
            self.prepared_data['dataset_names'] = data[0]['belongs_to__name']
            if data[0]['belongs_to__name'].startswith(settings.DATASET_ISISCB_NAME_PREFIX):
                self.prepared_data['dataset_typed_names'] = settings.DATASET_ISISCB_NAME_DISPLAY
            elif data[0]['belongs_to__name'].startswith(settings.DATASET_SHOT_NAME_PREFIX):
                self.prepared_data['dataset_typed_names'] = settings.DATASET_SHOT_NAME_DISPLAY

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

    def prepare_text(self, data):
        acrelation_names = []
        for a in data['acrelations']:
            if a['acrelation__authority__name']:
                acrelation_names.append(normalize(a['acrelation__authority__name']))
            elif a['acrelation__name_for_display_in_citation']:
                acrelation_names.append(normalize(a['acrelation__name_for_display_in_citation']))
        document = u' '.join([
            normalize(self.prepare_title(data)),
            normalize(data['description']),
            normalize(data['abstract'])
        ] + acrelation_names)

        if data['complete_citation']:
            document += ' ' + normalize(data['complete_citation'])
        return document

    def prepare_title(self, data):
        """
        Reviews are renamed to include the name of the reviewed work.
        """
        if data['type_controlled'] != Citation.REVIEW:
            if not data['title']:
                return u"Title missing"
            return remove_control_characters(data['title'])

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
                    return remove_control_characters(ccrelation['relations_to__subject__title'])
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
        return remove_control_characters(data['description'])

    def prepare_public(self, data):
        return data['public']

    def prepare_type(self, data):
        """
        Use the display representation of Citation.type_controlled.
        """
        return dict(Citation.TYPE_CHOICES).get(data['type_controlled'])

    def prepare_publication_date(self, data):
        attributes = data.get('attributes', None)

        freeform_dates = []

        for attr in attributes:
            if attr['attributes__type_controlled__name'] == settings.TIMELINE_PUBLICATION_DATE_ATTRIBUTE and attr['attributes__value_freeform']:
                date = attr['attributes__value_freeform']
                # IEXP-8: let's handle cases like 2001 - 2002 or 2001-01-02
                freeform_dates.append(date)
                patternYearSpan = re.match("([0-9]{4}).+?([0-9]{4})", date)
                if patternYearSpan:
                    for d in patternYearSpan.groups(): freeform_dates.append(d)
                    continue
                patternFullDate = re.match("([0-9]{4})-[0-9]{2}-[0-9]{2}", date)
                if patternFullDate:
                    for d in patternFullDate.groups(): freeform_dates.append(d)
                    continue
                # patterns e.g. 1999 (pub. 2000) or 1993-94
                patternBrackets = re.match(".*([0-9]{4}).*", date)
                if patternBrackets:
                    for d in patternBrackets.groups(): freeform_dates.append(d)
                    continue

        # this is a hack but it works, so :op
        date_id = None
        for attr in attributes:
            if attr['attributes__type_controlled__name'] == settings.TIMELINE_PUBLICATION_DATE_ATTRIBUTE:
                try:
                    attr = Attribute.objects.get(pk=attr['attributes__value__attribute_id'])
                    if type(attr.value.cvalue()) == list:
                        freeform_dates += attr.value.cvalue()
                    else:
                        freeform_dates.append(attr.value.cvalue().year)
                except ObjectDoesNotExist as E:
                    print("Attribute does not exist.")
                    print(E)

        if freeform_dates:
            return freeform_dates

        return ""

    def prepare_publication_date_for_sort(self, data):
        """
        If Citation.publication_data is not pre-filled, retrieve it from the
        formal Attribute (if possible).
        """

        if data['publication_date']:
            return data['publication_date']

        for attribute in data['attributes']:
            if attribute['attributes__type_controlled__name'] == settings.TIMELINE_PUBLICATION_DATE_ATTRIBUTE:
                return attribute['attributes__value_freeform']
        return ''

    def prepare_abstract(self, data):
        return remove_control_characters(data['abstract'])

    def prepare_complete_citation(self, data):
        return remove_control_characters(data['complete_citation'])

    def prepare_stub_record_status(self, data):
        return data['stub_record_status']

    def prepare_edition_details(self, data):
        return remove_control_characters(data['edition_details'])

    def prepare_physical_details(self, data):
        return remove_control_characters(data['physical_details'])

    def prepare_attributes(self, data):
        return [a['attributes__value_freeform'] for a in data['attributes']
                if a['attributes__public']]

    def prepare_page_string(self, data):
        """
        This is here just so that we can sort chapters in books.
        """
        if data['type_controlled'] not in [Citation.CHAPTER, Citation.ARTICLE]:
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


class AuthorityIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
    name = indexes.CharField(model_attr='name', indexed=False)
    description = indexes.CharField(model_attr='description', null=True, indexed=False)
    attributes = indexes.MultiValueField(indexed=False)
    authority_type = indexes.CharField(model_attr='type_controlled', indexed=False, null=True)
    public = indexes.BooleanField(model_attr='public', faceted=True, indexed=False)
    dates = indexes.MultiValueField(indexed=False)
    #citation_nr = indexes.CharField(indexed=False)

    def get_model(self):
        return Authority

    def prepare_text(self, obj):
        document = u' '.join([
            obj.normalized_name,
            obj.normalized_description,
        ] + [attr.value_freeform for attr in obj.attributes.all()])
        return document

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

        for k, v in list(self.prepared_data.items()):
            if type(v) is str:
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
        return [date.value_freeform for date in obj.attributes.filter(type_controlled__value_content_type__model__in=['datevalue', 'datetimevalue', 'isodatevalue', 'isodaterangevalue', 'daterangevalue'])]

    #def prepare_citation_nr(self, obj):
        #ACRelation.objects.filter(authority=obj, citation__public=True).distinct('citation_id').count()
