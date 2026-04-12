from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.contrib.postgres import fields as pg_fields

from isisdata.models import Authority, Citation, Tenant, CCRelation, ACRelation


class ImportedDataset(models.Model):
    """
    A model representing a dataset that has been imported. This is not meant to be a permanent record of the import, but just a way to group together records that were imported together and to track some basic information about the import.
    """
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    dataset_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    dataset_creator = models.CharField(max_length=255, blank=True, null=True)
    dataset_date = models.CharField(max_length=255, blank=True, null=True)
    task = models.ForeignKey('isisdata.AsyncTask', blank=True, null=True, on_delete=models.SET_NULL)

    owning_tenant = models.ForeignKey(
        Tenant,
        on_delete=models.SET_NULL,
        null=True
    )

class ImportedRecord(models.Model):
    class Meta(object):
        abstract = True

    imported_on = models.DateTimeField(auto_now_add=True)
    imported_by = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)

    dataset = models.ForeignKey(ImportedDataset, blank=True, null=True, on_delete=models.CASCADE)
    local_dataset_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)   

class ImportedAuthority(ImportedRecord):
    class Meta(object):
        verbose_name_plural = 'authority records'
        verbose_name = 'authority record'

    name = models.CharField(max_length=1000, db_index=True)
    
    @property
    def label(self):
        return self.name

    description = models.TextField(blank=True, null=True)

    type_controlled = models.CharField(max_length=2, null=True, blank=True,
                                       choices=Authority.TYPE_CHOICES,
                                       verbose_name="type",
                                       db_index=True)

    classification_system_object = models.ForeignKey('isisdata.ClassificationSystem', 
                                            blank=True, 
                                            null=True, 
                                            on_delete=models.SET_NULL)


    classification_code = models.CharField(max_length=255, blank=True,
                                           null=True, db_index=True)

    classification_hierarchy = models.CharField(max_length=255, blank=True,
                                                null=True, db_index=True)

    record_status = models.CharField(max_length=2, choices=Authority.STATUS_CHOICES,
                                     blank=True, null=True)
    
    # This is different than it is in the main model. Here we just add special person
    # information to the authority class, not as a separate subclass.
    personal_name_last = models.CharField(max_length=255, blank=True)
    personal_name_first = models.CharField(max_length=255, blank=True)
    personal_name_suffix = models.CharField(max_length=255, blank=True)
    personal_name_preferred = models.CharField(max_length=255, blank=True)

    # Generic reverse relations. These do not create new fields on the model.
    #  Instead, they provide an API for lookups back onto their respective
    #  target models via those models' GenericForeignKey relations.
    attributes = GenericRelation(
        'ImportedAttribute',
        related_query_name='authorities',
        content_type_field='source_content_type',
        object_id_field="source_instance_id")
    linkeddata_entries = GenericRelation(
        'ImportedLinkedData',
        related_query_name='authorities',
        content_type_field='subject_content_type',
        object_id_field='subject_instance_id')

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    @property
    def acrelations(self):
        """
        Provides access to related :class:`.ACRelation` instances directly.
        """
        query = Q(authority_id=self.id)
        return ImportedACRelation.objects.filter(public=True).filter(query)
    

class ImportedCitation(ImportedRecord):
    """
    An imported bibliographic record.
    """
    
    # Allowing blank values is not ideal, but many existing records lack titles.
    title = models.CharField(max_length=2000, blank=True)

    additional_titles = models.TextField(blank=True, null=True,
                                         help_text="Additional titles (not"
                                         " delimited, free text).")
    book_series = models.CharField(max_length=255, blank=True, null=True,
                                   help_text="Used for books, and potentially"
                                   " other works in a series.")

    created_native = models.DateTimeField(blank=True, null=True)
    
    subtype = models.ForeignKey('isisdata.CitationSubtype', blank=True, null=True, on_delete=models.SET_NULL)

    complete_citation =  models.TextField(blank=True, null=True,
                                         help_text="A complete citation that can be used to show a record if detailed information has not been entered yet.")

    stub_record_status = models.CharField(max_length=3, null=True, blank=True,
                                       choices=Citation.RECORD_STATUS_CHOICES)


    @property
    def label(self):
        return self.title

    description = models.TextField(null=True, blank=True)

    type_controlled = models.CharField(max_length=2, null=True, blank=True,
                                       verbose_name='type',
                                       choices=Citation.TYPE_CHOICES)

    
    abstract = models.TextField(blank=True, null=True)

    edition_details = models.TextField(blank=True, null=True)

    physical_details = models.CharField(max_length=255, null=True, blank=True)

    language = models.ManyToManyField('isisdata.Language', blank=True, null=True)

    part_details = models.OneToOneField('ImportedPartDetails', null=True, blank=True, on_delete=models.SET_NULL)

    publication_date = models.DateField(blank=True, null=True)

    related_citations = models.ManyToManyField('ImportedCitation', through='ImportedCCRelation',
                                               related_name='citations_related')
    related_authorities = models.ManyToManyField('ImportedAuthority',
                                                 through='ImportedACRelation',
                                                 related_name='citations_related')


    # Generic reverse relations. These do not create new fields on the model.
    #  Instead, they provide an API for lookups back onto their respective
    #  target models via those models' GenericForeignKey relations.
    attributes = GenericRelation(
        'ImportedAttribute',
        related_query_name='citations',
        content_type_field='source_content_type',
        object_id_field="source_instance_id")

    linkeddata_entries = GenericRelation(
        'ImportedLinkedData',
        related_query_name='citations',
        content_type_field='subject_content_type',
        object_id_field="subject_instance_id")

    @property
    def ccrelations(self):
        """
        Provides access to related :class:`.CCRelation` instances directly
        that are public.
        """
        query = Q(subject_id=self.id) | Q(object_id=self.id)
        return ImportedCCRelation.objects.filter(query)

    @property
    def all_ccrelations(self):
        query = Q(subject_id=self.id) | Q(object_id=self.id)
        return ImportedCCRelation.objects.filter(query)

    @property
    def get_new_authorities(self):
        return ImportedACRelation.objects.filter(citation=self, authority__isnull=False) 

    @property
    def get_existing_authorities(self):
        return ImportedACRelation.objects.filter(citation=self, existing_authority__isnull=False) 
    
    @property
    def get_ccrels_to_existing_citations(self):
        return self.ccrelations.filter(Q(existing_subject__isnull=False) | Q(existing_object__isnull=False))

    @property
    def get_ccrels_to_imported_citations(self):
        return self.ccrelations.filter(subject__isnull=False, object__isnull=False)

    @property
    def book(self):
        """
        Returns the public parent book object (which should only return something if this is a chapter)
        """
        return self.ccrelations.filter(object_id=self.id, type_controlled__in=[CCRelation.INCLUDES_CHAPTER]).first()
    
    @property
    def journal(self):
        """
        Returns the public periodical if this is an article or essay review.
        """
        if self.type_controlled not in [Citation.ARTICLE, Citation.ESSAY_REVIEW]:
            return None
        
        return self.acrelations.filter(type_controlled=ACRelation.PERIODICAL).first()

class ImportedPartDetails(models.Model):
    volume = models.CharField(max_length=255, null=True, blank=True)
    volume_free_text = models.CharField(max_length=255, null=True, blank=True)
    volume_begin = models.IntegerField(blank=True, null=True)
    volume_end = models.IntegerField(blank=True, null=True)
    issue_free_text = models.CharField(max_length=255, null=True, blank=True)
    issue_begin = models.IntegerField(blank=True, null=True)
    issue_end = models.IntegerField(blank=True, null=True)
    pages_free_text = models.CharField(max_length=255, null=True, blank=True)
    page_begin = models.IntegerField(blank=True, null=True)
    page_end = models.IntegerField(blank=True, null=True)

    sort_order = models.IntegerField(default=0)

    extent = models.PositiveIntegerField(blank=True, null=True)
    extent_note = models.TextField(blank=True, null=True)

    @property
    def pages(self):
        if not self.page_end and self.pages_free_text:
            return self.pages_free_text

        if self.page_begin and self.page_end:
            return u'{0} - {1}'.format(self.page_begin, self.page_end)

        return self.page_begin if self.page_begin else self.page_end

class ImportedACRelation(ImportedRecord):
    class Meta(object):
        verbose_name = 'authority-citation relationship'
        verbose_name_plural = 'authority-citation relationships'

    citation = models.ForeignKey('ImportedCitation', blank=True, null=True, on_delete=models.SET_NULL)

    authority = models.ForeignKey('ImportedAuthority', blank=True, null=True, on_delete=models.SET_NULL)
    existing_authority = models.ForeignKey(Authority, blank=True, null=True, on_delete=models.SET_NULL) 

    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    type_controlled = models.CharField(max_length=2, null=True, blank=True,
                                       choices=ACRelation.TYPE_CHOICES,
                                       verbose_name='relationship type')

    type_broad_controlled = models.CharField(max_length=2,
                                             choices=ACRelation.BROAD_TYPE_CHOICES,
                                             blank=True, null=True,
                                             verbose_name='relationship type (broad)')

    type_free = models.CharField(max_length=255,
                                 blank=True,
                                 verbose_name="relationship type (free-text)")

    name_for_display_in_citation = models.CharField(max_length=255, blank=True,
                                                    null=True)

    name_as_entered = models.CharField(max_length=255, null=True, blank=True)

    personal_name_first = models.CharField(max_length=255, null=True, blank=True)
    personal_name_last = models.CharField(max_length=255, null=True, blank=True)
    personal_name_suffix = models.CharField(max_length=255, null=True, blank=True)

    data_display_order = models.FloatField(default=1.0)

    def save(self, *args, **kwargs):
        if self.type_controlled is not None:
            if self.type_controlled in ACRelation.PERSONAL_RESPONS_TYPES:
                self.type_broad_controlled = ACRelation.PERSONAL_RESPONS
            elif self.type_controlled in ACRelation.SUBJECT_CONTENT_TYPES:
                self.type_broad_controlled = ACRelation.SUBJECT_CONTENT
            elif self.type_controlled in ACRelation.INSTITUTIONAL_HOST_TYPES:
                self.type_broad_controlled = ACRelation.INSTITUTIONAL_HOST
            elif self.type_controlled in ACRelation.PUBLICATION_HOST_TYPES:
                self.type_broad_controlled = ACRelation.PUBLICATION_HOST
        super(ImportedACRelation, self).save(*args, **kwargs)

    @property
    def get_existing_authority(self):
        return Authority.objects.filter(pk=self.existing_authority_id).first()

class ImportedCCRelation(ImportedRecord):
    
    class Meta(object):
        verbose_name = 'citation-citation relationship'
        verbose_name_plural = 'citation-citation relationships'

    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    type_controlled = models.CharField(max_length=3, null=True, blank=True,
                                       choices=CCRelation.TYPE_CHOICES)

    type_free = models.CharField(max_length=255, blank=True)

    subject = models.ForeignKey('ImportedCitation', related_name='relations_from', null=True, blank=True, on_delete=models.SET_NULL)
    existing_subject = models.ForeignKey(Citation, related_name='imported_relations_from', null=True, blank=True, on_delete=models.SET_NULL)

    object = models.ForeignKey('ImportedCitation', related_name='relations_to', null=True, blank=True, on_delete=models.SET_NULL)
    existing_object = models.ForeignKey(Citation, related_name='imported_relations_to', null=True, blank=True, on_delete=models.SET_NULL)

    data_display_order = models.FloatField(default=1.0)

class ImportedAttribute(models.Model):

    description = models.TextField(blank=True)

    # we'll just use one string here and worry about turning it into a controlled value later
    value = models.TextField(blank=True)

    value_citation = models.ForeignKey('ImportedCitation', on_delete=models.CASCADE)
    value_authority = models.ForeignKey('ImportedAuthority', on_delete=models.CASCADE)

    attribute_type = models.ForeignKey('isisdata.AttributeType', blank=True, null=True, on_delete=models.SET_NULL)  

    
class ImportedLinkedData(models.Model):
    
    description = models.TextField(blank=True)

    universal_resource_name = models.TextField(help_text="The value of the"
    " identifier (the actual DOI link or the value of the ISBN, etc). Will be a"
    " URN, URI, URL, or other unique identifier for a work, used as needed to"
    " provide information about how to find the digital object on the web or"
    " to identify the physical object uniquely.", db_index=True)

    resource_name = models.CharField(max_length=255, blank=True, null=True,
                                     help_text="Title of the resource that the"
                                               " URN links to.")

    url = models.TextField(blank=True, null=True,
                           help_text="If the URN is not an URL, you may"
                                     " optionally provide one here, for display"
                                     " purposes.")

    subject_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    subject_instance_id = models.CharField(max_length=200)
    subject = GenericForeignKey('subject_content_type',
                                'subject_instance_id')

    type_controlled = models.ForeignKey('isisdata.LinkedDataType', verbose_name='type',
                                        help_text="This field is used to"
    " determine what values are acceptable for the URN field, and to choose"
    " the correct display modality in the public-facing site and metadata", on_delete=models.SET_NULL, null=True)

    type_controlled_broad = models.CharField(max_length=255, blank=True)
    type_free = models.CharField(max_length=255, blank=True)

    access_status = models.CharField(max_length=255, blank=True, null=True)
    access_status_date_verified = models.DateField(blank=True, null=True)

    def __unicode__(self):
        values = (self.type_controlled,
                  self.universal_resource_name)
        return u'{0}: {1}'.format(*values)

    def __str__(self):
        values = (self.type_controlled,
                  self.universal_resource_name)
        return u'{0}: {1}'.format(*values)
    
class ImportedRecordStatus(models.Model):
    class Status(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Success'
        WARNING = 'WARNING', 'Warning'
        ERROR = 'ERROR', 'Error'

    dataset = models.ForeignKey(ImportedDataset, blank=True, null=True, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=Status.choices)
    message = models.TextField(blank=True, null=True)


class ImportedAuthorityStatus(ImportedRecordStatus):
    authority = models.ForeignKey(ImportedAuthority, on_delete=models.CASCADE, blank=True, null=True)

class ImportedCitationStatus(ImportedRecordStatus):
    citation = models.ForeignKey(ImportedCitation, on_delete=models.CASCADE, blank=True, null=True)    

class ImportedACRelationStatus(ImportedRecordStatus):
    acrelation = models.ForeignKey(ImportedACRelation, on_delete=models.CASCADE, blank=True, null=True)    

class ImportedCCRelationStatus(ImportedRecordStatus):
    ccrelation = models.ForeignKey(ImportedCCRelation, on_delete=models.CASCADE, blank=True, null=True)

    