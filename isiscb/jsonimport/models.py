from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.contrib.postgres import fields as pg_fields

from isisdata.models import Authority, Citation, Tenant, CCRelation, ACRelation


class ImportedRecord(models.Model):
    class Meta(object):
        abstract = True

    imported_on = models.DateTimeField(auto_now_add=True)
    imported_by = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)
    # TODO: part_of = models.ForeignKey('ImportAccession', on_delete=models.CASCADE)

class ImportedAuthority(ImportedRecord):
    class Meta(object):
        verbose_name_plural = 'authority records'
        verbose_name = 'authority record'

    name = models.CharField(max_length=1000, db_index=True)

    owning_tenant = models.ForeignKey(
        Tenant,
        on_delete=models.SET_NULL,
        related_name="owned_json_authorities",
        null=True
    )
    tenants = models.ManyToManyField(Tenant)

    @property
    def label(self):
        return self.name

    description = models.TextField(blank=True, null=True)

    type_controlled = models.CharField(max_length=2, null=True, blank=True,
                                       choices=Authority.TYPE_CHOICES,
                                       verbose_name="type",
                                       db_index=True)

    classification_system = models.CharField(max_length=4, blank=True,
                                             null=True, default=Authority.SPWC,
                                             choices=Authority.CLASS_SYSTEM_CHOICES,
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
    
    # CHECK: Had to add on_delete so chose cascade -> JD: deleting subtype shouldn't delete citation
    subtype = models.ForeignKey('isisdata.CitationSubtype', blank=True, null=True, on_delete=models.SET_NULL)

    complete_citation =  models.TextField(blank=True, null=True,
                                         help_text="A complete citation that can be used to show a record if detailed information has not been entered yet.")

    owning_tenant = models.ForeignKey(
        Tenant,
        on_delete=models.SET_NULL,
        related_name="owned_imported_citations",
        null=True
    )

    tenants = models.ManyToManyField(Tenant)

    stub_record_status = models.CharField(max_length=3, null=True, blank=True,
                                       choices=Citation.RECORD_STATUS_CHOICES)

    
    @property
    def tenant_ids(self):
        tenant_ids = [t.id for t in self.tenants.all()]
        if self.owning_tenant:
            tenant_ids.append(self.owning_tenant.id)
        return tenant_ids

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
                                                 related_name='authorities_related')


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
        return ImportedCCRelation.objects.filter(public=True).filter(query)

    @property
    def all_ccrelations(self):
        query = Q(subject_id=self.id) | Q(object_id=self.id)
        return ImportedCCRelation.objects.filter(query)
    
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

class ImportedCCRelation(ImportedRecord):
    
    class Meta(object):
        verbose_name = 'citation-citation relationship'
        verbose_name_plural = 'citation-citation relationships'

    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    type_controlled = models.CharField(max_length=3, null=True, blank=True,
                                       choices=ACRelation.TYPE_CHOICES)

    type_free = models.CharField(max_length=255, blank=True)

    subject = models.ForeignKey('ImportedCitation', related_name='relations_from', null=True, blank=True, on_delete=models.SET_NULL)

    object = models.ForeignKey('ImportedCitation', related_name='relations_to', null=True, blank=True, on_delete=models.SET_NULL)

    linkeddata_entries = GenericRelation('ImportedLinkedData',
                                         related_query_name='cc_relations',
                                         content_type_field='subject_content_type',
                                         object_id_field='subject_instance_id')

    data_display_order = models.FloatField(default=1.0)

class ImportedAttribute(models.Model):

    description = models.TextField(blank=True)

    # This is different than in the main model. We just have different fields for the 
    # different possible value types.
    value_int = models.IntegerField(default=0)
    value_float = models.FloatField()
    value_text = models.TextField(blank=True, null=True)
    value_char = models.CharField(max_length=2000)
    value_date_time = models.DateTimeField()
    value_date_range_start = pg_fields.ArrayField(
        models.DateField(),
        size=2,
    )
    value_citation = models.ForeignKey('ImportedCitation', on_delete=models.CASCADE)
    value_authority = models.ForeignKey('ImportedAuthority', on_delete=models.CASCADE)

    # Generic relation.
    source_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    source_instance_id = models.CharField(max_length=200)
    source = GenericForeignKey('source_content_type', 'source_instance_id')

    VALUE_TYPE_INT = "INT"
    VALUE_TYPE_STRING = "STRING"
    VALUE_TYPE_CHAR = "CHAR"
    VALUE_TYPE_DATE_TIME = "DATETIME"
    VALUE_TYPE_FLOAT = "FLOAT"
    VALUE_TYPE_CITATION = "CITATION"
    VALUE_TYPE_AUTHORITY = "AUTHORITY"

    VALUE_TYPE_CHOICES = {
        'Integer': VALUE_TYPE_INT,
        'String': VALUE_TYPE_STRING,
        'Char': VALUE_TYPE_CHAR,
        'Datetime': VALUE_TYPE_DATE_TIME,
        'Float': VALUE_TYPE_FLOAT,
        "Citation": VALUE_TYPE_CITATION,
        'Authority': VALUE_TYPE_AUTHORITY
    }
    type_controlled = models.CharField(choices=VALUE_TYPE_CHOICES,
                                           max_length=255,
                                           blank=True,
                                           null=True,
                                           db_index=True)

    
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
    

    