from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

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
    name = models.CharField(max_length=255)


class ImportedData(models.Model):
    class Meta:
        abstract = True

    imported_on = models.DateTimeField(auto_now_add=True)
    imported_by = models.ForeignKey(User, blank=True, null=True)
    part_of = models.ForeignKey('ImportAccession')

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
    type_controlled = models.CharField(max_length=2, null=True, blank=True)
    publication_date = models.CharField(max_length=100, null=True, blank=True)

    page_start = models.CharField(max_length=100, blank=True, null=True)
    page_end = models.CharField(max_length=100, blank=True, null=True)
    volume = models.CharField(max_length=100, blank=True, null=True)
    issue = models.CharField(max_length=100, blank=True, null=True)

    def __unicode__(self):
        return self.title


class DraftAuthority(ImportedData):
    """
    A shadow class for isisdata.Authority, in which most relation fields are
    replaced with text fields.

    This provides a way to represent raw data imported from Zotero, allowing a
    curator to inspect and correct records prior to addition to the main
    database. This could potentially support user-submitted entries in the
    future.
    """

    name = models.CharField(max_length=1000)
    name_last = models.CharField(max_length=255, null=True, blank=True)
    name_first = models.CharField(max_length=255, null=True, blank=True)
    name_suffix = models.CharField(max_length=255, null=True, blank=True)
    type_controlled = models.CharField(max_length=2, null=True, blank=True)

    resolutions = GenericRelation('InstanceResolutionEvent',
                                  related_query_name='authority_resolutions',
                                  content_type_field='for_model',
                                  object_id_field='for_instance_id')


class DraftACRelation(ImportedData):
    citation = models.ForeignKey('DraftCitation', related_name='authority_relations')
    authority = models.ForeignKey('DraftAuthority', related_name='citation_relations')
    type_controlled = models.CharField(max_length=2)
    type_broad_controlled = models.CharField(max_length=2)


class DraftCitationLinkedData(ImportedData):
    citation = models.ForeignKey('DraftCitation', related_name='linkeddata')
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)


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
