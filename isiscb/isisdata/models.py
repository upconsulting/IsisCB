from django.db import models
from django.db.models import Q
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from markupfield.fields import MarkupField

from simple_history.models import HistoricalRecords

from oauth2_provider.models import AbstractApplication

import datetime
import iso8601
import pickle
import uuid
from random import randint
import urlparse
import re
import bleach
import unidecode
import string
import unicodedata
from urlparse import urlsplit

from openurl.models import Institution

#from isisdata.templatetags.app_filters import linkify

def help_text(s):
    """
    Cleans up help strings so that we can write them in ways that are
    human-readable without screwing up formatting in the admin interface.
    """
    return re.sub('\s+', ' ', s).strip()


# TODO: remove this later.
def strip_punctuation(s):
    """
    Removes all punctuation characters from a string.
    """
    if not s:
        return ''
    if type(s) is str:    # Bytestring (default in Python 2.x).
        return s.translate(string.maketrans("",""), string.punctuation.replace('-', ''))
    else:                 # Unicode string (default in Python 3.x).
        translate_table = dict((ord(char), u'') for char
                                in u'!"#%\'()*+,./:;<=>?@[\]^_`{|}~')
        return s.translate(translate_table)


# TODO: remove this later.
def strip_tags(s):
    """
    Remove all tags without remorse.
    """
    return bleach.clean(s, tags={}, attributes={}, strip=True)


def remove_control_characters(s):
    return "".join(ch for ch in s if unicodedata.category(ch)[0]!="C")

# TODO: remove this later.
def normalize(s):
    """
    Convert to ASCII.
    Remove HTML.
    Remove punctuation.
    Lowercase.
    """
    if not s:
        return ''

    return remove_control_characters(strip_punctuation(strip_tags(unidecode.unidecode(s))).lower())

# TODO: is that the best way to do this???
def strip_hyphen(s):
    """
    Remove hyphens and replace with space.
    Need to find hyphenated names.
    """
    if not s:
        return ''

    return s.replace('-', ' ')


VALUETYPES = Q(model='textvalue') | Q(model='charvalue') | Q(model='intvalue') \
            | Q(model='datetimevalue') | Q(model='datevalue') \
            | Q(model='floatvalue') | Q(model='locationvalue')



class Value(models.Model):
    """
    A :class:`.Value` represents the value of an :class:`Attribute`\.

    This class should not be instantiated directly, but rather via a subclass.
    Subclasses should have a field ``value``, which can be of any type.

    Subclasses can optionally provide a staticmethd ``convert`` that yields a
    Python object from an alphanumeric input, and raises ValidationError for
    bad data.
    """
    attribute = models.OneToOneField('Attribute', related_name='value',
                                     help_text=help_text("""
    The Attribute to which this Value belongs."""))

    child_class = models.CharField(max_length=255, help_text=help_text("""
    Name of the child model for this instance."""))

    @classmethod
    def is_valid(model, value):
        try:
            if hasattr(model, 'convert'):
                model.convert(value)
        except ValidationError as E:
            raise E

    def save(self, *args, **kwargs):
        if hasattr(self, 'convert') and self.value is not None:
            self.value = self.convert(self.value)
        if self.child_class == '' or self.child_class is None:
            self.child_class = type(self).__name__
        return super(Value, self).save(*args, **kwargs)

    def get_child_class(self):
        """
        Retrieve the instance of the child class for this Value.
        """
        cclass_name = self.child_class.lower()
        if hasattr(self, cclass_name):
            return getattr(self, cclass_name)
        return None

    @property
    def display(self):
        """
        Provides a rendered unicode representation of the value.
        """
        child = self.get_child_class()
        if hasattr(child, 'render'):
            return child.render()
        return self.__unicode__()

    def render(self):
        """
        Override this method in a subclass to control how it is rendered for
        display in views.
        """
        return unicode(self.value)

    def cvalue(self):
        cclass = self.get_child_class()
        if cclass is not None and cclass != '':
            return cclass.value
        return None
    cvalue.short_description = 'value'

    def __unicode__(self):
        try:
            return unicode(self.cvalue())
        except:
            return u''


class TextValue(Value):
    """
    A long/freeform text value.
    """
    value = models.TextField()

    class Meta:
        verbose_name = 'text (long)'


class CharValue(Value):
    """
    A string value (max 2000 characters).
    """
    value = models.CharField(max_length=2000)

    @staticmethod
    def convert(value):
        if len(value) > 2000:
            raise ValidationError('Must be 2,000 characters or less')
        return value

    class Meta:
        verbose_name = 'text (short)'


class IntValue(Value):
    """
    An integer value.
    """
    value = models.IntegerField(default=0)

    @staticmethod
    def convert(value):
        try:
            return int(value)
        except ValueError:
            raise ValidationError('Must be an integer')

    class Meta:
        verbose_name = 'integer'


class DateTimeValue(Value):
    """
    ISO 8601 datetime value.
    """
    value = models.DateTimeField()

    @staticmethod
    def convert(value):
        if type(value) is datetime.datetime:
            return value
        try:
            return iso8601.parse_date(value)
        except iso8601.ParseError:
            raise ValidationError('Not a valid ISO8601 date')

    class Meta:
        verbose_name = 'date and time'


class DateValue(Value):
    """
    An ISO 8601 date value.
    """
    value = models.DateField()

    def save(self, *args, **kwargs):
        """
        Override to update Citation.publication_date, if this DateValue belongs
        to an Attribute of type "PublicationDate".
        """
        super(DateValue, self).save(*args, **kwargs)    # Save first.

        if self.attribute.type_controlled.name == 'PublicationDate':
            self.attribute.source.publication_date = self.value
            self.attribute.source.save()

    @staticmethod
    def convert(value):
        if type(value) is datetime.date:
            return value
        try:
            return iso8601.parse_date(value).date()
        except iso8601.ParseError:
            raise ValidationError('Not a valid ISO8601 date')

    class Meta:
        verbose_name = 'date'


class FloatValue(Value):
    """
    A floating-point number value.
    """
    value = models.FloatField()

    @staticmethod
    def convert(value):
        try:
            return float(value)
        except ValueError:
            raise ValidationError('Must be a floating point number')

    class Meta:
        verbose_name = 'floating point number'


class LocationValue(Value):
    """
    A location value. Points to an instance of :class:`.Location`\.
    """
    value = models.ForeignKey('Location')   # TODO: One to One?

    class Meta:
        verbose_name = 'location'


VALUE_MODELS = [
    (int,               IntValue),
    (float,             FloatValue),
    (datetime.datetime, DateTimeValue),
    (datetime.date,     DateValue),
    (str,               CharValue),
    (unicode,           CharValue),
]


class CuratedMixin(models.Model):
    """
    Curated objects have an audit history and curatorial notes attached to them.
    """

    class Meta:
        abstract = True

    administrator_notes = models.TextField(blank=True, null=True,
                                           help_text=help_text("""
    Curatorial discussion about the record."""))

    record_history = models.TextField(blank=True, null=True,
                                      help_text=help_text("""
    Notes about the provenance of the information in this record. e.g. 'supplied
    by the author,' 'imported from SHOT bibliography,' 'generated by crawling UC
    Press website'"""))

    modified_on = models.DateTimeField(auto_now=True, blank=True, null=True,
                                       help_text=help_text("""
    Date and time at which this object was last updated."""))

    modified_by = models.ForeignKey(User, null=True, blank=True,
                                    help_text=help_text("""
    The most recent user to modify this object."""))

    public = models.BooleanField(default=True, help_text=help_text("""
    Controls whether this instance can be viewed by end users."""))

    @property
    def created_on(self):
        """
        The date and time at which this object was created.

        Retrieves the date of the (one and only) creation HistoricalRecord for
        an instance.
        """
        return self.history.get(history_type='+').history_date

    @property
    def created_by(self):
        """
        The user who created this object.

        Retrieves the user on the (one and only) creation HistoricalRecord for
        an instance.
        """
        return self.history.get(history_type='+').history_user

    created_on_fm = models.DateTimeField(null=True, help_text=help_text("""
    Value of CreatedOn from the original FM database."""))

    created_by_fm = models.CharField(max_length=255, blank=True, null=True,
                                    help_text=help_text("""
    Value of CreatedBy from the original FM database."""))

    modified_on_fm = models.DateTimeField(null=True,
                                          verbose_name="modified on (FM)",
                                          help_text=help_text("""
    Value of ModifiedBy from the original FM database."""))

    modified_by_fm = models.CharField(max_length=255, blank=True,
                                      verbose_name="modified by (FM)",
                                      help_text=help_text("""
    Value of ModifiedOn from the original FM database."""))

    @property
    def _history_user(self):
        return self.modified_by

    @_history_user.setter
    def _history_user(self, value):
        self.modified_by = value

    @property
    def _history_date(self):
        return self.modified_on

    @_history_date.setter
    def _history_date(self, value):
        self.modified_on = value


class ReferencedEntity(models.Model):
    """
    Provides a custom ID field and an URI field, and associated methods.

    TODO: implement an accession field.
    """

    class Meta:
        abstract = True

    id = models.CharField(max_length=200, primary_key=True,
                          help_text=help_text("""
    In the format {PRE}{ZEROS}{NN}, where PRE is a three-letter prefix
    indicating the record type (e.g. CBA for Authority), NN is an integer,
    and ZEROS is 0-9 zeros to pad NN such that ZEROS+NN is nine characters
    in length."""))

    # uri = models.URLField(blank=True)
    @property
    def uri(self):
        return self.generate_uri

    def generate_uri(self):
        """
        Create a new Unique Resource Identifier.
        """
        values = type(self).__name__.lower(), self.id
        return urlparse.urlunparse(('http', settings.DOMAIN,
                                    'isis/{0}/{1}/'.format(*values), '', '', ''))

    def save(self, *args, **kwargs):
        if self.id is None or self.id == '':
            # Ensure that this ID is unique.
            while True:
                id = '{0}{1}'.format(self.ID_PREFIX, "%09d" % randint(0,999999999))
                if self.__class__.objects.filter(id=id).count() == 0:
                    break   # TODO: find a better/simpler way?
            self.id = id

        if self.uri == '':
            self.uri = self.generate_uri()
        super(ReferencedEntity, self).save(*args, **kwargs)


class Language(models.Model):
    """
    Represents a contemporary human language.

    Populate this using fixtures/language.json to load ISO 639-1 language codes.
    """

    id = models.CharField(max_length=2, primary_key=True,
                          help_text=help_text("""
    Language code (e.g. ``en``)."""))

    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name


class Citation(ReferencedEntity, CuratedMixin):
    """
    A bibliographic record.
    """
    ID_PREFIX = 'CBB'

    history = HistoricalRecords()

    # Allowing blank values is not ideal, but many existing records lack titles.
    title = models.CharField(max_length=2000, blank=True,
                             help_text=help_text("""
    The name to be used to identify the resource. For reviews that traditionally
    have no title, this should be added as something like "[Review of Title
    (Year) by Author]"."""))

    @property
    def normalized_title(self):
        """
        Title stripped of HTML, punctuation, and normalized to ASCII.
        """
        return normalize(self.title)

    @property
    def normalized_abstract(self):
        """
        Abstract stripped of HTML, punctuation, and normalized to ASCII.
        """

        return normalize(self.abstract)

    @property
    def normalized_description(self):
        return normalize(self.description)


    @property
    def label(self):
        return self.title

    description = models.TextField(null=True, blank=True,
                                   help_text=help_text("""
    Used for additional bibliographic description, such as content summary. For
    abstracts use the 'Abstract' field."""))

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

    type_controlled = models.CharField(max_length=2, null=True, blank=True,
                                       verbose_name='type',
                                       choices=TYPE_CHOICES,
                                       help_text=help_text("""
    This list can be extended to the resource types specified by Doublin Core
    Recource Types http://dublincore.org/documents/resource-typelist/
    """))

    abstract = models.TextField(blank=True, help_text=help_text("""
    Abstract or detailed summaries of a work.
    """))

    edition_details = models.TextField(blank=True, help_text=help_text("""
    Use for describing the edition or version of the resource. Include names of
    additional contributors if necessary for clarification (such as translators,
    introduction by, etc). Always, use relationship table to list contributors
    (even if they are specified here).
    """))

    physical_details = models.CharField(max_length=255, blank=True,
                                        help_text=help_text("""
    For describing the physical description of the resource. Use whatever
    information is appropriate for the type of resource.
    """))

    # Storing this in the model would be kind of hacky. This will make it easier
    #  to do things like sort or filter by language.
    language = models.ManyToManyField('Language', help_text=help_text("""
    Language of the resource. Multiple languages can be specified.
    """))

    # TODO: This relation should be from PartDetails to Citation, to support
    #  inlines in the Admin.
    part_details = models.OneToOneField('PartDetails', null=True, blank=True,
                                        help_text=help_text("""
    New field: contains volume, issue, page information for works that are parts
    of larger works.
    """))

    publication_date = models.DateField(blank=True, null=True,
                                        help_text=help_text("""
    Used for search and sort functionality. Does not replace Attribute
    functionality.
    """))

    related_citations = models.ManyToManyField('Citation', through='CCRelation',
                                               related_name='citations_related')
    related_authorities = models.ManyToManyField('Authority',
                                                 through='ACRelation',
                                                 related_name='authorities_related')

    EXTERNAL_PROOF = 'EX'
    QUERY_PROOF = 'QU'
    HOLD = 'HO'
    RLG_CORRECT = 'RC'
    ACTION_CHOICES = (
        (EXTERNAL_PROOF, 'External Proof'),
        (QUERY_PROOF, 'Query Proof'),
        (HOLD, 'Hold'),
        (RLG_CORRECT, 'RLG Correct')
    )
    record_action = models.CharField(max_length=2, blank=True,
                                     choices=ACTION_CHOICES,
                                     help_text=help_text("""
    Used to track the record through curation process.
    """))

    CONTENT_LIST = 'CL'
    SOURCE_BOOK = 'SB'
    SCOPE = 'SC'
    FIX_RECORD = 'FX'
    DUPLICATE = 'DP'
    DELETE = 'DL'
    ISISRLG = 'RL'
    STATUS_CHOICES = (
        (CONTENT_LIST, 'Content List'),
        (SOURCE_BOOK, 'Source Book'),
        (SCOPE, 'Scope'),
        (FIX_RECORD, 'Fix Record'),
        (DUPLICATE, 'Duplicate'),
        (DELETE, 'Delete'),
        (ISISRLG, 'Isis RLG'),  # TODO: What is this, precisely?
    )
    status_of_record = models.CharField(max_length=2, choices=STATUS_CHOICES,
                                        blank=True, help_text="""
    Used to control printing in the paper volume of the CB.
    """)

    # Generic reverse relations. These do not create new fields on the model.
    #  Instead, they provide an API for lookups back onto their respective
    #  target models via those models' GenericForeignKey relations.
    attributes = GenericRelation(
        'Attribute',
        related_query_name='citations',
        content_type_field='source_content_type',
        object_id_field="source_instance_id")

    linkeddata_entries = GenericRelation(
        'LinkedData',
        related_query_name='citations',
        content_type_field='subject_content_type',
        object_id_field="subject_instance_id")

    tracking_entries = GenericRelation(
        'Tracking',
        related_query_name='citations',
        content_type_field='subject_content_type',
        object_id_field='subject_instance_id')

    def __unicode__(self):
        return strip_tags(self.title)

    @property
    def ccrelations(self):
        """
        Provides access to related :class:`.CCRelation` instances directly.
        """
        query = Q(subject_id=self.id) | Q(object_id=self.id)
        return CCRelation.objects.filter(public=True).filter(query)

    @property
    def acrelations(self):
        """
        Provides access to related :class:`.ACRelation` instances directly.
        """
        query = Q(citation_id=self.id)
        return ACRelation.objects.filter(public=True).filter(query)

    @property
    def get_all_contributors(self):
        query = Q(citation_id=self.id) & Q(type_broad_controlled__in=['PR'], data_display_order__lt=30)
        return ACRelation.objects.filter(public=True).filter(query).order_by('data_display_order')


class Authority(ReferencedEntity, CuratedMixin):
    ID_PREFIX = 'CBA'

    class Meta:
        verbose_name_plural = 'authority records'
        verbose_name = 'authority record'

    history = HistoricalRecords()

    name = models.CharField(max_length=1000, help_text=help_text("""
    Name, title, or other main term for the authority as will be displayed.
    """))

    @property
    def normalized_name(self):
        """
        Title stripped of HTML, punctuation, and normalized to ASCII.
        """
        return strip_hyphen(normalize(self.name))

    @property
    def normalized_description(self):
        """
        Description stripped of HTML, punctuation, and normalized to ASCII.
        """
        return normalize(self.description)


    @property
    def label(self):
        return self.name

    description = models.TextField(blank=True, null=True,
                                   help_text=help_text("""
    A brief description that will be displayed to help identify the authority.
    Such as, brief bio or a scope note. For classification terms will be text
    like 'Classification term from the XXX classification schema.'
    """))

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
    PUBLISHER = 'PU'
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
        (PUBLISHER, 'Publisher'),
    )
    type_controlled = models.CharField(max_length=2, null=True, blank=True,
                                       choices=TYPE_CHOICES,
                                       verbose_name="type",
                                       help_text=help_text("""
    Specifies authority type. Each authority thema has its own list of
    controlled type vocabulary.
    """))

    SWP = 'SWP'
    NEU = 'NEU'
    MW = 'MW'
    SHOT = 'SHOT'
    SEARCH = 'SAC'
    CLASS_SYSTEM_CHOICES = (
        (SWP, 'SWP'),
        (NEU, 'Neu'),
        (MW, 'MW'),
        (SHOT, 'SHOT'),
        (SEARCH, 'SAC')
    )
    classification_system = models.CharField(max_length=4, blank=True,
                                             null=True,
                                             choices=CLASS_SYSTEM_CHOICES,
                                             help_text=help_text("""
    Specifies the classification system that is the source of the authority.
    Used to group resources by the Classification system. The system used
    currently is the Weldon System. All the other ones are for reference or
    archival purposes only.
    """))

    classification_code = models.CharField(max_length=255, blank=True,
                                           null=True, help_text=help_text("""
    alphanumeric code used in previous classification systems to describe
    classification terms. Primarily of historical interest only. Used primarily
    for Codes for the classificationTerms. however, can be used for other
    kinds of terms as appropriate.
    """))

    classification_hierarchy = models.CharField(max_length=255, blank=True,
                                                null=True,
                                                help_text=help_text("""
    Used for Classification Terms to describe where they fall in the
    hierarchy.
    """))

    ACTIVE = 'AC'
    DUPLICATE = 'DU'
    REDIRECT = 'RD'
    DELETE = 'DL'
    INACTIVE = 'IN'
    STATUS_CHOICES = (
        (ACTIVE, 'Active'),
        (DUPLICATE, 'Duplicate'),
        (REDIRECT, 'Redirect'),
        (INACTIVE, 'Inactive'),
    )
    record_status = models.CharField(max_length=2, choices=STATUS_CHOICES,
                                     blank=True, null=True)

    redirect_to = models.ForeignKey('Authority', blank=True, null=True)

    # Generic reverse relations. These do not create new fields on the model.
    #  Instead, they provide an API for lookups back onto their respective
    #  target models via those models' GenericForeignKey relations.
    attributes = GenericRelation(
        'Attribute',
        related_query_name='authorities',
        content_type_field='source_content_type',
        object_id_field="source_instance_id")
    linkeddata_entries = GenericRelation(
        'LinkedData',
        related_query_name='authorities',
        content_type_field='subject_content_type',
        object_id_field='subject_instance_id')
    tracking_entries = GenericRelation(
        'Tracking',
        related_query_name='authorities',
        content_type_field='subject_content_type',
        object_id_field='subject_instance_id')

    def __unicode__(self):
        return self.name

    @property
    def aarelations(self):
        """
        Provides access to related :class:`.AARelation` instances directly.
        """
        query = Q(subject_id=self.id) | Q(object_id=self.id)
        return AARelation.objects.filter(public=True).filter(query)

    @property
    def acrelations(self):
        """
        Provides access to related :class:`.ACRelation` instances directly.
        """
        query = Q(authority_id=self.id)
        return ACRelation.objects.filter(public=True).filter(query)


class Person(Authority):
    """
    People are special cases of authority records, with several unique fields.
    """
    history = HistoricalRecords()

    # QUESTION: These seems specific to the PERSON type. Should we be modeling
    #  Authority types separately? E.g. each type could be a child class of
    #  Authority, and we can preserve generic relations to Attributes using
    #  multi-table inheritance. Another reason to do this is that we want
    #  users to be able to "claim" their PERSON record -- this is much more
    #  straightforward with separate models.
    # are those calculated?
    personal_name_last = models.CharField(max_length=255)
    personal_name_first = models.CharField(max_length=255)
    personal_name_suffix = models.CharField(max_length=255, blank=True)


class ACRelation(ReferencedEntity, CuratedMixin):
    """
    A relation between a :class:`.Authority` and a :class:`.Citaton`\.

    For example, between a paper and its author(s), a book and its place of
    publication, etc.
    """
    ID_PREFIX = 'ACR'

    class Meta:
        verbose_name = 'authority-citation relationship'
        verbose_name_plural = 'authority-citation relationships'

    history = HistoricalRecords()

    citation = models.ForeignKey('Citation')
    authority = models.ForeignKey('Authority')

    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    # TODO: conditional validation on these fields.
    # Allowed values depend on the value of the Type.Broad,controlled
    # if Type.Broad.controlled = 'HasPersonalResponsibilityFor'
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
    type_controlled = models.CharField(max_length=2, null=True, blank=True,
                                       choices=TYPE_CHOICES,
                                       verbose_name='relationship type',
                                       help_text=help_text("""
    Used to specify the nature of the relationship between authority (as the
    subject) and the citation (as the object).
    """))

    PERSONAL_RESPONS = 'PR'
    SUBJECT_CONTENT = 'SC'
    INSTITUTIONAL_HOST = 'IH'
    PUBLICATION_HOST = 'PH'
    BROAD_TYPE_CHOICES = (
        (PERSONAL_RESPONS, 'Has Personal Responsibility For'),
        (SUBJECT_CONTENT, 'Provides Subject Content About'),
        (INSTITUTIONAL_HOST, 'Is Institutional Host Of'),
        (PUBLICATION_HOST, 'Is Publication Host Of')
    )
    type_broad_controlled = models.CharField(max_length=2,
                                             choices=BROAD_TYPE_CHOICES,
                                             blank=True,
                                             verbose_name='relationship type (broad)',
                                             help_text=help_text("""
    Used to specify the nature of the relationship between authority (as the
    subject) and the citation (as the object) more broadly than the relationship
    type.
    """))

    type_free = models.CharField(max_length=255,
                                 blank=True,
                                 verbose_name="relationship type (free-text)",
                                 help_text="""
    Free-text description of the role that the authority plays in the
    citation (e.g. 'introduction by', 'dissertation supervisor', etc).
    """)

    name_for_display_in_citation = models.CharField(max_length=255,
                                                    help_text=help_text("""
    Display for the authority as it is to be used when being displayed with the
    citation. Eg. the form of the author's name as it appears on a
    publication--say, J.E. Koval--which might be different from the name of the
    authority--Jenifer Elizabeth Koval.
    """))

    name_as_entered = models.CharField(max_length=255, blank=True,
                                       help_text=help_text("""
    Display for the authority as it is has been used in a publication.
    """))

    data_display_order = models.FloatField(default=1.0, help_text=help_text("""
    Position at which the authority should be displayed in the citation detail
    view. Whole numbers or decimals can be used.
    """))

    # currently not used
    confidence_measure = models.FloatField(default=1.0,
                                           validators = [MinValueValidator(0),
                                                         MaxValueValidator(1)],
                                           help_text=help_text("""
    Currently not used: will be used to assess the confidence of the link in the
    event that there is some ambiguity.
    """))

    relationship_weight = models.FloatField(default=1.0,
                                            validators = [MinValueValidator(0),
                                                          MaxValueValidator(2)],
                                            help_text=help_text("""
    Currently not used: helps to assess how significant this relationship is--to
    be used mostly in marking subjects.
    """))

    # Generic reverse relations. These do not create new fields on the model.
    #  Instead, they provide an API for lookups back onto their respective
    #  target models via those models' GenericForeignKey relations.
    attributes = GenericRelation(
        'Attribute',
        related_query_name='ac_relations',
        content_type_field='source_content_type',
        object_id_field="source_instance_id")

    linkeddata_entries = GenericRelation(
        'LinkedData',
        related_query_name='ac_relations',
        content_type_field='subject_content_type',
        object_id_field='subject_instance_id')

    tracking_entries = GenericRelation(
        'Tracking',
        related_query_name='ac_relations',
        content_type_field='subject_content_type',
        object_id_field='subject_instance_id')

    def _render_type_controlled(self):
        try:
            return dict(self.TYPE_CHOICES)[self.type_controlled]
        except KeyError:
            return u'None'

    def __unicode__(self):
        values = (self.citation, self._render_type_controlled(), self.authority)
        return u'{0} - {1} - {2}'.format(*values)


class AARelation(ReferencedEntity, CuratedMixin):
    """
    A relation between two :class:`.Authority` instances.

    For example, between a teacher and a student, an employee and an
    instutution, between two events, etc.
    """
    ID_PREFIX = 'AAR'

    class Meta:
        verbose_name = 'authority-authority relationship'
        verbose_name_plural = 'authority-authority relationships'

    # Currently not used, but crucial to development of next generation relationship tools:
    name = models.CharField(max_length=255, blank=True)
    # Currently not used, but crucial to development of next generation relationship tools:
    description = models.TextField(blank=True)

    IDENTICAL_TO = 'IDTO'
    PARENT_OF = 'PAOF'
    PREVIOUS_TO = 'PRETO'
    OFFICER_OF = 'OFOF'
    ASSOCIATED_WITH = 'ASWI'
    TYPE_CHOICES = (
        (IDENTICAL_TO, 'Is Identical To'),
        (PARENT_OF, 'Is Parent Of'),
        (PREVIOUS_TO, 'Happened Previous To'),
        (OFFICER_OF, 'Is Officer Of'),
        (ASSOCIATED_WITH, 'Is Associated With')
    )
    type_controlled = models.CharField(max_length=5, choices=TYPE_CHOICES,
                                       null=True, blank=True,
                                       help_text=help_text("""
    Controlled term specifying the nature of the relationship
    (the predicate between the subject and object).
    """))

    type_free = models.CharField(max_length=255, blank=True,
                                 help_text=help_text("""
    Free text description of the relationship.
    """))

    subject = models.ForeignKey('Authority', related_name='relations_from')
    object = models.ForeignKey('Authority', related_name='relations_to')

    # missing from Stephen's list: objectType, subjectType

    # Generic reverse relations. These do not create new fields on the model.
    #  Instead, they provide an API for lookups back onto their respective
    #  target models via those models' GenericForeignKey relations.
    attributes = GenericRelation('Attribute', related_query_name='aa_relations',
                                 content_type_field='source_content_type',
                                 object_id_field="source_instance_id")
    linkeddata_entries = GenericRelation('LinkedData',
                                         related_query_name='aa_relations',
                                         content_type_field='subject_content_type',
                                         object_id_field='subject_instance_id')
    tracking_entries = GenericRelation('Tracking',
                                       related_query_name='aa_relations',
                                       content_type_field='subject_content_type',
                                       object_id_field='subject_instance_id')

    def _render_type_controlled(self):
        try:
            return dict(self.TYPE_CHOICES)[self.type_controlled]
        except KeyError:
            return u'None'


    def __unicode__(self):
        values = (self.subject, self._render_type_controlled(), self.object)
        return u'{0} - {1} - {2}'.format(*values)


class CCRelation(ReferencedEntity, CuratedMixin):
    """
    A relation between two :class:`.Citation` instances.

    For example, between a review article and the book that it reviews,
    between an article and an article that it cites, or between a chapter and
    the book in which it appears.
    """
    ID_PREFIX = 'CCR'

    class Meta:
        verbose_name = 'citation-citation relationship'
        verbose_name_plural = 'citation-citation relationships'

    history = HistoricalRecords()

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
                                       choices=TYPE_CHOICES,
                                       help_text=help_text("""
    Type of relationship between two citation records.
    """))

    type_free = models.CharField(max_length=255, blank=True,
                                 help_text=help_text("""
    Type of relationship as used in the citation.
    """))

    subject = models.ForeignKey('Citation', related_name='relations_from')
    object = models.ForeignKey('Citation', related_name='relations_to')

    # Generic reverse relations. These do not create new fields on the model.
    #  Instead, they provide an API for lookups back onto their respective
    #  target models via those models' GenericForeignKey relations.
    attributes = GenericRelation('Attribute', related_query_name='cc_relations',
                                 content_type_field='source_content_type',
                                 object_id_field="source_instance_id")
    linkeddata_entries = GenericRelation('LinkedData',
                                         related_query_name='cc_relations',
                                         content_type_field='subject_content_type',
                                         object_id_field='subject_instance_id')
    tracking_entries = GenericRelation('Tracking',
                                       related_query_name='cc_relations',
                                       content_type_field='subject_content_type',
                                       object_id_field='subject_instance_id')

    def _render_type_controlled(self):
        try:
            return dict(self.TYPE_CHOICES)[self.type_controlled]
        except KeyError:
            return u'None'


    def __unicode__(self):
        values = (self.subject, self._render_type_controlled(), self.object)
        return u'{0} - {1} - {2}'.format(*values)


class LinkedDataType(models.Model):
    class Meta:
        verbose_name = 'linked data type'
        verbose_name_plural = 'linked data types'

    name = models.CharField(max_length=255, unique=True)
    pattern = models.CharField(max_length=255, blank=True,
                               help_text=help_text("""
    Regular expression used to validate :class:`.LinkedData` values.
    """))

    def is_valid(self, value):
        if not self.pattern:
            return

        if re.match(self.pattern, value) is None:
            message = 'Does not match pattern for {0}'.format(self.name)
            print 'asdf'
            raise ValidationError(message)

    def __unicode__(self):
        return self.name


class AttributeType(models.Model):
    name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255, blank=True, null=True,
                                    help_text=help_text("""
    The "name" attribute is not always suitable for display in public views.
    This field provides the name to be displayed to users.
    """))

    value_content_type = models.ForeignKey(ContentType,
                                           limit_choices_to=VALUETYPES,
                                           related_name='attribute_value')

    def __unicode__(self):
        return u'{0} ({1})'.format(self.name, self.value_content_type.model)


class Attribute(ReferencedEntity, CuratedMixin):
    ID_PREFIX = 'ATT'
    history = HistoricalRecords()

    description = models.TextField(blank=True, help_text=help_text("""
    Additional information about this attribute.
    """))

    value_freeform = models.CharField(max_length=255,
                                      verbose_name="freeform value",
                                      blank=True,
                                      help_text=help_text("""
    Non-normalized value, e.g. an approximate date, or a date range.
    """))

    # Generic relation.
    source_content_type = models.ForeignKey(ContentType)
    source_instance_id = models.CharField(max_length=200)
    source = GenericForeignKey('source_content_type', 'source_instance_id')

    # The selected AttributeType determines the type of Value (i.e. Value
    #  subclass) that can be related to this Attribute.
    type_controlled = models.ForeignKey('AttributeType', verbose_name='type',
                                        help_text=help_text("""
    The "type" field determines what kinds of values are acceptable for this
    attribute.
    """))

    # TODO: Instead of saving this in the Attribute model, we may want to create
    #  a mechanism for grouping/ranking AttributeTypes.
    type_controlled_broad = models.CharField(max_length=255, blank=True)
    type_free = models.CharField(max_length=255, blank=True)

    def __unicode__(self):
        try:
            return u'{0}: {1}'.format(self.type_controlled.name,
                                      self.value.cvalue())
        except:
            return u''


class PartDetails(models.Model):
    """
    New field: contains volume, issue, page information for works that are parts
    of larger works.
    """

    class Meta:
        verbose_name = 'part detail'
        verbose_name_plural = 'part details'


    volume = models.CharField(max_length=255, blank=True)
    volume_free_text = models.CharField(max_length=255, blank=True)
    volume_begin = models.IntegerField(blank=True, null=True)
    volume_end = models.IntegerField(blank=True, null=True)
    issue_free_text = models.CharField(max_length=255, blank=True)
    issue_begin = models.IntegerField(blank=True, null=True)
    issue_end = models.IntegerField(blank=True, null=True)
    pages_free_text = models.CharField(max_length=255, blank=True)
    page_begin = models.IntegerField(blank=True, null=True)
    page_end = models.IntegerField(blank=True, null=True)

    sort_order = models.IntegerField(default=0, help_text=help_text(""""
    New field: provides a sort order for works that are part of a larger work.
    """))


class Place(models.Model):
    """
    A concept of locality associated with a particular point or region in space.
    """
    name = models.CharField(max_length=255)
    gis_location = models.ForeignKey('Location', blank=True, null=True)
    gis_schema = models.ForeignKey('LocationSchema', blank=True, null=True)


class LocationSchema(models.Model):
    """
    Represents an SRID.
    """

    name = models.CharField(max_length=255)


class Location(models.Model):
    """
    SRID-agnostic decimal coordinate.
    """

    NORTH = 'N'
    SOUTH = 'S'
    EAST = 'E'
    WEST = 'W'
    LAT_CARDINAL = (
        (NORTH, 'North'),
        (SOUTH, 'South')
    )
    LON_CARDINAL = (
        (EAST, 'East'),
        (WEST, 'West')
    )
    latitude = models.FloatField()
    latitude_direction = models.CharField(max_length=1, choices=LAT_CARDINAL)

    longitude = models.FloatField()
    longitude_direction = models.CharField(max_length=1, choices=LON_CARDINAL)


class LinkedData(ReferencedEntity, CuratedMixin):
    """
    An external resource identifier or locator.
    """
    ID_PREFIX = "LED"

    class Meta:
        verbose_name = 'linked data entry'
        verbose_name_plural = 'linked data entries'

    history = HistoricalRecords()

    description = models.TextField(blank=True)

    universal_resource_name = models.CharField(max_length=255,
                                               help_text=help_text("""
    The value of the identifier (the actual DOI link or the value of the ISBN,
    etc). Will be a URN, URI, URL, or other unique identifier for a work, used
    as needed to provide information about how to find the digital object on the
    web or to identify the physical object uniquely.
    """))

    # In the Admin, we should limit the queryset to Authority and Citation
    #  instances only.
    subject_content_type = models.ForeignKey(ContentType)
    subject_instance_id = models.CharField(max_length=200)
    subject = GenericForeignKey('subject_content_type',
                                'subject_instance_id')

    type_controlled = models.ForeignKey('LinkedDataType', verbose_name='type',
                                        help_text=help_text("""
    The "type" field determines what kinds of values are acceptable for this
    linked data entry.
    """))


    type_controlled_broad = models.CharField(max_length=255, blank=True)
    type_free = models.CharField(max_length=255, blank=True)

    def __unicode__(self):
        values = (self.type_controlled,
                  self.universal_resource_name)
        return u'{0}: {1}'.format(*values)


class Tracking(ReferencedEntity, CuratedMixin):
    """
    An audit entry for tracking the status of records in the curatorial process.

    This is a higher-level concept than the History audit log, which records
    only changes to entries.
    """
    ID_PREFIX = 'TRK'

    history = HistoricalRecords()

    tracking_info = models.CharField(max_length=255, blank=True)

    HSTM_UPLOAD = 'HS'
    PRINTED = 'PT'
    AUTHORIZED = 'AU'
    PROOFED = 'PD'
    FULLY_ENTERED = 'FU'
    BULK_DATA = 'BD'
    TYPE_CHOICES = (
        (HSTM_UPLOAD, 'HSTM Upload'),
        (PRINTED, 'Printed'),
        (AUTHORIZED, 'Authorized'),
        (PROOFED, 'Proofed'),
        (FULLY_ENTERED, 'Fully Entered'),
        (BULK_DATA, 'Bulk Data Update')
    )

    type_controlled = models.CharField(max_length=2, null=True, blank=True,
                                       choices=TYPE_CHOICES)

    subject_content_type = models.ForeignKey(ContentType)
    subject_instance_id = models.CharField(max_length=200)
    subject = GenericForeignKey('subject_content_type',
                                'subject_instance_id')

    notes = models.TextField(blank=True)


class Annotation(models.Model):
    """
    User-generated content associated with a specific entity.
    """
    subject_content_type = models.ForeignKey(ContentType)
    subject_instance_id = models.CharField(max_length=200)
    subject = GenericForeignKey('subject_content_type',
                                'subject_instance_id')

    subject_field = models.CharField(max_length=255, blank=True, null=True,
                                     help_text=help_text("""
    The name of the field in ``subject`` to which this annotation refers. For
    example, ``title``.
    """))

    created_by = models.ForeignKey(User, related_name='annotations', null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)


    child_class = models.CharField(max_length=255, blank=True,
                                   help_text=help_text("""
    Name of the child model for this instance.
    """))

    def save(self, *args, **kwargs):
        if self.child_class == '' or self.child_class is None:
            self.child_class = type(self).__name__
        return super(Annotation, self).save(*args, **kwargs)

    def get_child_class(self):
        return getattr(self, self.child_class.lower())

    @property
    def byline(self):
        return u'{0} {1}'.format(self.created_by.username, self.created_on.strftime('on %d %b, %Y at %I:%M %p'))


def linkify(s, *args, **kwargs):
    def shorten_display(attrs, new=False):
        """
        Remove characters from the middle of the link, and strip protocol.
        """
        parse_result = urlsplit(attrs['_text'])
        attrs['_text'] = parse_result.netloc + parse_result.path
        if parse_result.query:
            attrs['_text'] += '?' + parse_result.query
        attrs['_text'] = attrs['_text'][:10] + u'...' + attrs['_text'][-10:]
        return attrs

    # Just in case we want to add other callbacks from outside...
    if 'callbacks' not in kwargs:
        kwargs.update({'callbacks': []})
    kwargs['callbacks'].append(shorten_display)
    return bleach.linkify(s, *args, **kwargs)


class Comment(Annotation):
    """
    A free-form text :class:`.Annotation`\.
    """
    text = models.TextField()

    @property
    def snippet(self):
        return self.text[:min(100, len(self.text))] + u'...'

    @property
    def linkified(self):
        return linkify(self.text)

    class Meta:
        get_latest_by = 'created_on'


class TagAppellation(Annotation):
    """
    The appellation of an entity with a :class:`.Tag`\.
    """
    tag = models.ForeignKey('Tag')


class Tag(models.Model):
    """
    An :class:`.Annotation` from a controlled vocabulary
    (:class:`.TaggingSchema`).
    """
    schema = models.ForeignKey('TaggingSchema', related_name='tags')
    value = models.CharField(max_length=255)
    description = models.TextField()

    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)


class TaggingSchema(models.Model):
    """
    A named set of :class:`.Tag`\s.
    """
    name = models.CharField(max_length=255)

    created_by = models.ForeignKey(User, related_name='tagging_schemas')
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)


class SearchQuery(models.Model):
    user = models.ForeignKey(User, related_name='searches')
    created_on = models.DateTimeField(auto_now_add=True)
    parameters = models.CharField(max_length=500)
    search_models = models.CharField(max_length=500, null=True, blank=True)
    selected_facets = models.CharField(max_length=500, null=True, blank=True)
    name = models.CharField(max_length=255, blank=True, null=True,
                            help_text=help_text("""
    Provide a memorable name so that you can find this search later.
    """))

    saved = models.BooleanField(default=False)


class UserProfile(models.Model):
    """
    Supports additional self-curated information about Users.
    """
    user = models.OneToOneField(User, related_name='profile')

    affiliation = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    bio = MarkupField(markup_type='markdown', blank=True, null=True)

    share_email = models.BooleanField(default=False, help_text=help_text("""
    A user can indicate whether or not their email address should be made
    public."""))

    resolver_institution = models.ForeignKey(Institution, blank=True, null=True,
                                             related_name='users',
                                             help_text=help_text("""
    A user can select an institution for which OpenURL links should be
    generated while searching."""))

    authority_record = models.OneToOneField(Authority, blank=True, null=True,
                                            related_name='associated_user',
                                            help_text=help_text("""
    A user can 'claim' an Authority record, asserting that the record refers to
    theirself."""))
