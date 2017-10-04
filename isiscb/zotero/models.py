from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.core.urlresolvers import reverse

from isisdata.models import Dataset, Citation, Authority, Language
from isisdata.utils import normalize
from unidecode import unidecode

from itertools import groupby

import re


def help_text(s):
    """
    Cleans up help strings so that we can write them in ways that are
    human-readable without screwing up formatting in the admin interface.
    """
    return re.sub('\s+', ' ', s).strip()


class ImportAccession(models.Model):
    imported_on = models.DateTimeField(auto_now_add=True)
    imported_by = models.ForeignKey(User, blank=True, null=True)
    name = models.CharField(max_length=255, db_index=True)
    ingest_to = models.ForeignKey(Dataset, null=True)
    processed = models.BooleanField(default=False)

    @property
    def citations_ok(self):
        ok = []
        for draftcitation in self.draftcitation_set.all():
            ready = True
            for relation in draftcitation.authority_relations.all():
                # ISISCB-1048: if a citation is already been resolve it's ok
                if not relation.authority.processed and not draftcitation.resolutions:
                    ready = False
                    break
            if ready:
                ok.append(draftcitation.id)
        return self.draftcitation_set.filter(pk__in=ok)

    @property
    def citations_ready(self):
        fields = ['authority_relations__authority__processed',
                  'authority_relations__authority__id']
        qs = self.draftcitation_set.filter(processed=False).values('id', *fields)
        key = lambda o: o['id']
        ready = []
        for i, group in groupby(sorted(qs, key=key), key=key):
            instance_ready = True
            for o in group:
                if o['authority_relations__authority__id'] and not o['authority_relations__authority__processed']:
                    instance_ready = False
                    break
            if instance_ready:
                ready.append(i)
        return self.draftcitation_set.filter(pk__in=ready)

    @property
    def citations_remaining(self):
        return self.draftcitation_set.filter(processed=False)


    @property
    def resolved(self):
        return self.draftauthority_set.filter(processed=False).count() == 0

    def __unicode__(self):
        return self.name


class ImportedData(models.Model):
    class Meta:
        abstract = True

    imported_on = models.DateTimeField(auto_now_add=True)
    imported_by = models.ForeignKey(User, blank=True, null=True)
    part_of = models.ForeignKey('ImportAccession')

    # dataset = models.CharField(max_length=255, blank=True, null=True)
    # editor = models.CharField(max_length=255, blank=True, null=True)

    processed = models.BooleanField(default=False, help_text=help_text("""
    Indicates whether or not a record has been inspected, and a corresponding
    entry/entries in isisdata have been created. When True, a record should
    be hidden from the curation interface by default.
    """))


class DraftCitation(ImportedData):
    """
    A shadow class for isisdata.Citation, in which most relation fields are
    replaced with text fields.

    This provides a way to represent raw data imported from Zotero, allowing a
    curator to inspect and correct records prior to addition to the main
    database. This could potentially support user-submitted entries in the
    future.
    """

    title = models.CharField(max_length=1000, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    abstract = models.TextField(null=True, blank=True)
    extra = models.TextField(null=True, blank=True)
    """ISISCB-788: "extra" data should be stored in a separate field."""

    source_data = models.TextField(null=True, blank=True)
    """Raw data from which this record was generated."""

    BOOK = 'BO'
    ARTICLE = 'AR'
    CHAPTER = 'CH'
    REVIEW = 'RE'
    ESSAY_REVIEW = 'ES'
    THESIS = 'TH'
    EVENT = 'EV'
    PRESENTATION = 'PR'
    INTERACTIVE = 'IN'
    WEBSITE = 'WE'
    APPLICATION = 'AP'

    TYPE_CHOICES = (
        (BOOK, 'Book'),
        (ARTICLE, 'Article'),
        (CHAPTER, 'Chapter'),
        (REVIEW, 'Review'),
        (ESSAY_REVIEW, 'Essay Review'),
        (THESIS, 'Thesis'),
        (EVENT, 'Event'),
        (PRESENTATION, 'Presentation'),
        (INTERACTIVE, 'Interactive Resource'),
        (WEBSITE, 'Website'),
        (APPLICATION, 'Application'),
    )
    type_controlled = models.CharField(choices=TYPE_CHOICES, max_length=2, null=True, blank=True)
    publication_date = models.CharField(max_length=100, null=True, blank=True)

    page_start = models.CharField(max_length=100, blank=True, null=True)
    page_end = models.CharField(max_length=100, blank=True, null=True)
    pages_free_text = models.CharField(max_length=100, blank=True, null=True)
    volume = models.CharField(max_length=100, blank=True, null=True)
    issue = models.CharField(max_length=100, blank=True, null=True)
    book_series = models.CharField(max_length=255, blank=True, null=True)
    extent = models.PositiveIntegerField(blank=True, null=True)
    extent_note = models.TextField(blank=True, null=True)

    physical_details = models.CharField(max_length=255, null=True, blank=True)

    language = models.ForeignKey(Language, blank=True, null=True)

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('data_draftcitation', args=(self.id,))

    resolutions = GenericRelation('InstanceResolutionEvent',
                                  related_query_name='citation_resolutions',
                                  content_type_field='for_model',
                                  object_id_field='for_instance_id')


class DraftAuthority(ImportedData):
    """
    A shadow class for isisdata.Authority, in which most relation fields are
    replaced with text fields.

    This provides a way to represent raw data imported from Zotero, allowing a
    curator to inspect and correct records prior to addition to the main
    database. This could potentially support user-submitted entries in the
    future.
    """

    PERSON = 'PE'
    INSTITUTION = 'IN'
    TIME_PERIOD = 'TI'
    GEOGRAPHIC_TERM = 'GE'
    SERIAL_PUBLICATION = 'SE'
    CLASSIFICATION_TERM = 'CT'
    CONCEPT = 'CO'
    CREATIVE_WORK = 'CW'
    EVENT = 'EV'
    CROSSREFERENCE = 'CR'
    TYPE_CHOICES = (
        (PERSON, 'Person'),
        (INSTITUTION, 'Institution'),
        (TIME_PERIOD, 'Time Period'),
        (GEOGRAPHIC_TERM, 'Geographic Term'),
        (SERIAL_PUBLICATION, 'Serial Publication'),
        (CLASSIFICATION_TERM, 'Classification Term'),
        (CONCEPT, 'Concept'),
        (CREATIVE_WORK, 'Creative Work'),
        (EVENT, 'Event'),
        (CROSSREFERENCE, 'Cross-reference'),
    )
    name = models.CharField(max_length=1000)
    name_last = models.CharField(max_length=255, null=True, blank=True)
    name_first = models.CharField(max_length=255, null=True, blank=True)
    name_suffix = models.CharField(max_length=255, null=True, blank=True)
    type_controlled = models.CharField(max_length=2, choices=TYPE_CHOICES,
                                       null=True, blank=True)

    name_for_sort = models.CharField(max_length=2000, blank=True, null=True)

    resolutions = GenericRelation('InstanceResolutionEvent',
                                  related_query_name='authority_resolutions',
                                  content_type_field='for_model',
                                  object_id_field='for_instance_id')

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('data_draftauthority', args=(self.id,))

    @property
    def resolved(self):
        return self.resolutions.count() > 0

    class Meta:
        verbose_name = 'draft authority record'
        verbose_name_plural = 'draft authority records'

    def save(self, *args, **kwargs):
        self.name_for_sort = normalize(unidecode(self.name))
        super(DraftAuthority, self).save(*args, **kwargs)



class DraftCCRelation(ImportedData):
    """
    A relation between two :class:`.Citation` instances.

    For example, between a review article and the book that it reviews,
    between an article and an article that it cites, or between a chapter and
    the book in which it appears.
    """


    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)


    INCLUDES_CHAPTER = 'IC'
    INCLUDES_SERIES_ARTICLE = 'ISA'
    REVIEW_OF = 'RO'
    REVIEWED_BY = 'RB'
    RESPONDS_TO = 'RE'
    ASSOCIATED_WITH = 'AS'
    TYPE_CHOICES = (
        (INCLUDES_CHAPTER, 'Includes Chapter'),
        (INCLUDES_SERIES_ARTICLE, 'Includes Series Article'),
        (REVIEW_OF, 'Is Review Of'),
        (RESPONDS_TO, 'Responds To'),
        (ASSOCIATED_WITH, 'Is Associated With'),
        (REVIEWED_BY, 'Is Reviewed By')
    )
    type_controlled = models.CharField(max_length=3, null=True, blank=True,
                                       choices=TYPE_CHOICES)

    type_free = models.CharField(max_length=255, blank=True, null=True)

    subject = models.ForeignKey('DraftCitation', related_name='relations_from')
    object = models.ForeignKey('DraftCitation', related_name='relations_to')

    resolutions = GenericRelation('InstanceResolutionEvent',
                                  related_query_name='ccrelation_resolutions',
                                  content_type_field='for_model',
                                  object_id_field='for_instance_id')


class DraftACRelation(ImportedData):
    citation = models.ForeignKey('DraftCitation',
                                 related_name='authority_relations')
    authority = models.ForeignKey('DraftAuthority',
                                  related_name='citation_relations')

    # TODO: implement mechanism in save() to populate type_broad_controlled
    #  based on the value of type_controlled.
    AUTHOR = 'AU'
    EDITOR = 'ED'
    ADVISOR = 'AD'
    CONTRIBUTOR = 'CO'
    TRANSLATOR = 'TR'
    # if Type.Broad.controlled = 'ProvidesSubjectContentAbout'
    SUBJECT = 'SU'
    CATEGORY = 'CA'
    # if Type.Broad.controlled = 'IsInstitutionalHostOf'
    PUBLISHER = 'PU'
    SCHOOL = 'SC'
    INSTITUTION = 'IN'
    MEETING = 'ME'
    # if Type.Broad.controlled = 'IsPublicationHostOf'
    PERIODICAL = 'PE'
    BOOK_SERIES = 'BS'
    TYPE_CHOICES = (
        (AUTHOR, 'Author'),
        (EDITOR, 'Editor'),
        (ADVISOR, 'Advisor'),
        (CONTRIBUTOR, 'Contributor'),
        (TRANSLATOR, 'Translator'),
        (SUBJECT, 'Subject'),
        (CATEGORY, 'Category'),
        (PUBLISHER, 'Publisher'),
        (SCHOOL, 'School'),
        (INSTITUTION, 'Institution'),
        (MEETING, 'Meeting'),
        (PERIODICAL, 'Periodical'),
        (BOOK_SERIES, 'Book Series')
    )
    type_controlled = models.CharField(max_length=2, blank=True, null=True,
                                       choices=TYPE_CHOICES)
    type_broad_controlled = models.CharField(max_length=2, blank=True,
                                             null=True)

    resolutions = GenericRelation('InstanceResolutionEvent',
                                  related_query_name='acrelation_resolutions',
                                  content_type_field='for_model',
                                  object_id_field='for_instance_id')
    data_display_order = models.FloatField(default=1.0)


class DraftCitationLinkedData(ImportedData):
    citation = models.ForeignKey('DraftCitation', related_name='linkeddata')
    name = models.CharField(max_length=255)
    value = models.TextField()


class DraftAuthorityLinkedData(ImportedData):
    authority = models.ForeignKey('DraftAuthority', related_name='linkeddata')
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)


class DraftAttribute(ImportedData):
    citation = models.ForeignKey('DraftCitation', related_name='attributes')
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)


class InstanceResolutionEvent(models.Model):
    for_model = models.ForeignKey(ContentType, related_name='instanceresolutions_for')
    for_instance_id = models.PositiveIntegerField()
    for_instance = GenericForeignKey('for_model', 'for_instance_id')

    to_model =  models.ForeignKey(ContentType, related_name='instanceresolutions_to')
    to_instance_id = models.CharField(max_length=1000)
    to_instance = GenericForeignKey('to_model', 'to_instance_id')


class FieldResolutionEvent(models.Model):
    for_model = models.ForeignKey(ContentType, related_name='fieldresolutions_for')
    for_field = models.CharField(max_length=100)
    for_value = models.CharField(max_length=1000)

    to_value = models.CharField(max_length=1000)
