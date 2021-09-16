from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
from builtins import object
from django.db import models
from django.db.models import Q
from django.contrib.postgres import fields as pg_fields
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractBaseUser
from django.core.validators import MaxValueValidator, MinValueValidator,int_list_validator
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.urls import reverse as core_reverse
from django.utils.safestring import mark_safe
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
import jsonpickle


from markupfield.fields import MarkupField

from simple_history.models import HistoricalRecords

from oauth2_provider.models import AbstractApplication

from isisdata.utils import *

import copy, datetime, iso8601, pickle, uuid, urllib.parse, re, bleach, unidecode
from random import randint
import string, unicodedata
from urllib.parse import urlsplit

from openurl.models import Institution

#from isisdata.templatetags.app_filters import linkify



VALUETYPES = Q(model='textvalue') | Q(model='charvalue') | Q(model='intvalue') \
            | Q(model='datetimevalue') | Q(model='datevalue') \
            | Q(model='floatvalue') | Q(model='locationvalue') \
            | Q(model='isodatevalue') | Q(model='isodaterangevalue') \
            | Q(model='authorityvalue') | Q(model='citationvalue')


class Value(models.Model):
    """
    A :class:`.Value` represents the value of an :class:`Attribute`\.

    This class should not be instantiated directly, but rather via a subclass.
    Subclasses should have a field ``value``, which can be of any type.

    Subclasses can optionally provide a staticmethd ``convert`` that yields a
    Python object from an alphanumeric input, and raises ValidationError for
    bad data.
    """
    # CHECK: Had to add on_delete so chose cascade -> JD: I believe this makes sense
    attribute = models.OneToOneField('Attribute', related_name='value',
                                     help_text=help_text("""
    The Attribute to which this Value belongs."""), on_delete=models.CASCADE)

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
        return str(self.value)

    def cvalue(self):
        cclass = self.get_child_class()
        if cclass is not None and cclass != '':
            return cclass.value
        return None
    cvalue.short_description = 'value'

    def __unicode__(self):
        try:
            return str(self.cvalue())
        except:
            return u''

    def __str__(self):
        try:
            return str(self.cvalue())
        except:
            return u''


class TextValue(Value):
    """
    A long/freeform text value.
    """
    value = models.TextField()

    def __unicode__(self):
        return self.value

    class Meta(object):
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

    def __unicode__(self):
        return self.value

    class Meta(object):
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

    def __unicode__(self):
        return str(self.value)

    class Meta(object):
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

    def __unicode__(self):
        return self.value.isoformat()

    class Meta(object):
        verbose_name = 'date and time'


class ISODateRangeValue(Value):
    start = pg_fields.ArrayField(models.IntegerField(default=0), size=3)
    end = pg_fields.ArrayField(models.IntegerField(default=0), size=3)

    PARTS = ['start', 'end']

    def _valuegetter(self):
        return [[v for v in getattr(self, part) if v != 0] for part in self.PARTS if getattr(self, part)]

    def _valuesetter(self, value):
        try:
            value = ISODateRangeValue.convert(value)
        except ValidationError:
            raise ValueError('Invalid value for ISODateRangeValue: ' + value.__repr__())

        for i, part in enumerate(self.PARTS):
            if i >= len(value):
                setattr(self, part, [0, 0, 0])
            else:
                v = value[i]
                if type(v) not in [list, tuple]:
                    v = [v]
                setattr(self, part, v)
        # for part_value, part in zip(value, self.PARTS):
            # setattr(self, part, part_value)

    value = property(_valuegetter, _valuesetter)

    @staticmethod
    def convert(value):
        if type(value) in [tuple, list] and len(value) == 2:
            value = list(value)
            for i in range(2):
                value[i] = ISODateValue.convert(value[i])
        elif type(value) in [tuple, list] and len(value) == 1 and type(value[0]) in [tuple, list]:
            try:
                value = ISODateValue.convert(value[0])
            except:
                raise ValidationError('Not a valid ISO8601 date range')
        else:
            try:
                value = ISODateValue.convert(value)
            except:
                raise ValidationError('Not a valid ISO8601 date range')
        return value

    def __unicode__(self):
        def _coerce(val):
            val = str(val)
            if val.startswith('-') and len(val) < 5:
                val = val[0] + str.zfill(val[1:], 4)
            elif len(val) == 3:
                val = str.zfill(val, 4)
            elif len(val) == 1:
                val = str.zfill(val, 2)
            return val

        return u'%s to %s' % tuple(['-'.join([_coerce(v) for v in getattr(self, part) if v != 0]) for part in self.PARTS])

    def __str__(self):
        def _coerce(val):
            val = str(val)
            if val.startswith('-') and len(val) < 5:
                val = val[0] + str.zfill(val[1:], 4)
            elif len(val) == 3:
                val = str.zfill(val, 4)
            elif len(val) == 1:
                val = str.zfill(val, 2)
            return val

        return u'%s to %s' % tuple(['-'.join([_coerce(v) for v in getattr(self, part) if v != 0]) for part in self.PARTS])

    def render(self):
        return self.__unicode__()

    class Meta(object):
        verbose_name = 'ISO date range'


class DateRangeValue(Value):
    value = pg_fields.ArrayField(
        models.DateField(),
        size=2,
    )

    @staticmethod
    def convert(value):
        if type(value) in [tuple, list] and len(value) == 2:
            for i in range(2):
                if type(value[i]) is not datetime.date:
                    try:
                        value[i] = iso8601.parse_date(value[i]).date()
                    except iso8601.ParseError:
                        raise ValidationError('Not a valid ISO8601 date')
            # The first element should always be a lower value than the second.
            return sorted(value)
        else:
            raise ValidationError('Must be a 2-tuple or 2-element list')

    def __unicode__(self):
        return u'%s to %s' % tuple([part.isodate() for part in self.value])

    def __str__(self):
        return u'%s to %s' % tuple([part.isodate() for part in self.value])

    class Meta(object):
        verbose_name = 'date range'


class ISODateValue(Value):
    """
    A variable-precision date.
    """
    PARTS = [u'year', u'month', u'day']

    year = models.IntegerField(default=0)
    month = models.IntegerField(default=0)
    day = models.IntegerField(default=0)

    datetime_formats = [
        '%m/%d/%Y %I:%M:%S %p',
        '%m/%d/%Y %I:%M %p'
    ]
    date_formats = [
        '%m/%d/%Y',
        '%Y'
    ]

    @property
    def as_date(self):
        """
        Attempt to coerce a value to ``datetime.date``.
        """
        value = self.__unicode__()
        for format in ISODateValue.datetime_formats + ISODateValue.date_formats:
            try:
                return datetime.datetime.strptime(value, format)
            except ValueError:
                pass
        try:
            return iso8601.parse_date(value).date()
        except ValueError:
            pass
        raise ValueError('Could not coerce value to datetime: %s' % value)

    def save(self, *args, **kwargs):
        """
        Override to update Citation.publication_date, if this DateValue belongs
        to an Attribute of type "PublicationDate".
        """


        if self.attribute.type_controlled.name == 'PublicationDate':
            try:
                self.attribute.source.publication_date = self.as_date
                self.attribute.source.save()
            except (ValueError, AttributeError):
                print('Error settings publication_date on source')

        super(ISODateValue, self).save(*args, **kwargs)    # Save first.

    def _valuegetter(self):
        return [getattr(self, part) for part in self.PARTS if getattr(self, part) != 0]

    def _valuesetter(self, value):
        # raise AttributeError('grrargh')

        try:
            value = ISODateValue.convert(value)
        except ValidationError:
            raise ValueError('Invalid value for ISODateValue: %s' % value.__repr__())

        for i, part in enumerate(self.PARTS):
        # for i, v in enumerate(value):
            if i >= len(value):
                setattr(self, part, 0)
            else:
                setattr(self, part, value[i])

    def __unicode__(self):
        def _coerce(val):
            val = str(val)
            if val.startswith('-') and len(val) < 5:
                val = val[0] + str.zfill(val[1:], 4)
            elif len(val) == 3:
                val = str.zfill(val, 4)
            elif len(val) == 1:
                val = str.zfill(val, 2)
            return val

        return '-'.join([_coerce(v) for v in self.value])

    def __str__(self):
        def _coerce(val):
            val = str(val)
            if val.startswith('-') and len(val) < 5:
                val = val[0] + str.zfill(val[1:], 4)
            elif len(val) == 3:
                val = str.zfill(val, 4)
            elif len(val) == 1:
                val = str.zfill(val, 2)
            return val

        return '-'.join([_coerce(v) for v in self.value])

    def render(self):
        return self.__unicode__()

    value = property(_valuegetter, _valuesetter)

    @property
    def precision(self):
        last = None
        for part in self.PARTS:
            if getattr(self, part) == 0:
                return last
            last = copy.copy(part)
        return part

    @staticmethod
    def convert(value):

        if type(value) in [tuple, list]:
            value = list(value)
        elif type(value) in [str, str]:

            pre = u''
            if value.startswith('-'):   # Preserve negative years.
                value = value[1:]
                pre = u'-'
            value = value.split('-')
            value[0] = pre + value[0]

        elif type(value) is int:   # We assume that it is just a year.
            value = [value]
        elif type(value) is datetime.datetime:
            date = value.date()
            value = [date.year, date.month, date.day]
        elif type(value) is datetime.date:
            value = [value.year, value.month, value.day]
        else:
            raise ValidationError('Not a valid ISO8601 date')

        if len(value) > 0:
            if int(value[0]) > 0 and (type(value[0]) in [str, str] and len(value[0]) > 4):
                raise ValidationError('Not a valid ISO8601 date')
            elif int(value[0]) < 0 and (type(value[0]) in [str, str] and len(value[0]) > 5):
                raise ValidationError('Not a valid ISO8601 date')
            for v in value[1:]:
                if type(v) in [str, str] and len(v) != 2:
                    raise ValidationError('Not a valid ISO8601 date')
        try:

            return [int(v) for v in value if v]
        except NameError:
            raise ValidationError('Not a valid ISO8601 date')

    class Meta(object):
        verbose_name = 'isodate'


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

    def __unicode__(self):
        return self.value.isoformat()

    def __str__(self):
        return self.value.isoformat()

    class Meta(object):
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

    def __unicode__(self):
        return str(self.value)

    class Meta(object):
        verbose_name = 'floating point number'


class LocationValue(Value):
    """
    A location value. Points to an instance of :class:`.Location`\.
    """
    # CHECK: Had to add on_delete so chose cascade -> JD: cascade should be fine
    value = models.ForeignKey('Location', on_delete=models.CASCADE)   # TODO: One to One? JD: yes I believe so

    def __unicode__(self):
        return self.value.__unicode__

    def __str__(self):
        return self.value.__unicode__

    class Meta(object):
        verbose_name = 'location'

class CitationValue(Value):
    """
    A citation value. Points to an instance of :class:`.Citation`\.
    """
    # CHECK: Had to add on_delete so chose cascade -> JD: since we don't delete Authorities at the moment, this is probably fine
    value = models.ForeignKey('Citation', on_delete=models.CASCADE)
    name = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return str(self.value)

    def __str__(self):
        return str(self.value)

    class Meta(object):
        verbose_name = 'citation'

    @staticmethod
    def convert(value):
        if type(value) is Citation:
            return value

        try:
            return Citation.objects.get(pk=value)
        except ValueError:
            raise ValidationError('Must be the id of an existing citation.')


class AuthorityValue(Value):
    """
    An authority value. Points to an instance of :class:`.Authority`\.
    """
    # CHECK: Had to add on_delete so chose cascade -> JD: since we don't delete Authorities at the moment, this is probably fine
    value = models.ForeignKey('Authority', on_delete=models.CASCADE)
    name = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return str(self.value)

    def __str__(self):
        return str(self.value)

    class Meta(object):
        verbose_name = 'authority'

    @staticmethod
    def convert(value):
        if type(value) is Authority:
            return value

        try:
            return Authority.objects.get(pk=value)
        except ValueError:
            raise ValidationError('Must be the id of an existing authority.')


VALUE_MODELS = [
    (int,               IntValue),
    (float,             FloatValue),
    (datetime.datetime, DateTimeValue),
    (datetime.date,     ISODateValue),
    (str,               CharValue),
    (str,           CharValue),
    (tuple,             DateRangeValue),
    (list,              DateRangeValue),
]


class CuratedMixin(models.Model):
    """
    Curated objects have an audit history and curatorial notes attached to them.
    """

    class Meta(object):
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
    # CHECK: Had to add on_delete so chose cascade ->  JD: superclass for many, if user is delete, objects should not all be deleted
    modified_by = models.ForeignKey(User, null=True, blank=True,
                                    help_text=help_text("""
    The most recent user to modify this object."""), on_delete=models.SET_NULL)

    public = models.BooleanField(default=True, help_text=help_text("""
    Controls whether this instance can be viewed by end users."""))

    ACTIVE = 'Active'
    DUPLICATE = 'Duplicate'
    REDIRECT = 'Redirect'
    INACTIVE = 'Inactive'
    STATUS_CHOICES = (
        (ACTIVE, 'Active'),
        (DUPLICATE, 'Delete'),
        (REDIRECT, 'Redirect'),
        (INACTIVE, 'Inactive'),
    )
    record_status_value = models.CharField(choices=STATUS_CHOICES,
                                           max_length=255,
                                           blank=True,
                                           null=True,
                                           default=ACTIVE,
                                           db_index=True)

    record_status_explanation = models.CharField(max_length=255,
                                                 blank=True,
                                                 null=True)

    def save(self, *args, **kwargs):
        """
        The record_status_value field controls whether or not the record is
        public.
        """
        if self.record_status_value == CuratedMixin.ACTIVE:
            self.public = True
        else:
            self.public = False

        # fixing issue with simple history where modifier is not saved
        if hasattr(HistoricalRecords.thread, 'request'):
            if HistoricalRecords.thread.request.user:
                self.modified_by = HistoricalRecords.thread.request.user

        return super(CuratedMixin, self).save(*args, **kwargs)

    def save_obj(self, user, *args, **kwargs):
        self.modified_by = user
        self.save(args, kwargs)

    @property
    def created_on(self):
        """
        The date and time at which this object was created.

        Retrieves the date of the (one and only) creation HistoricalRecord for
        an instance.
        """
        try:
            record = self.history.filter(history_type='+').first()
            if record:
                return record.history_date
        except ObjectDoesNotExist:
            if self.created_on_fm:
                return self.created_on_fm
            else:
                first = self.history.order_by('modified_on').first()
                if first:
                    return first.history_date
        return None

    @property
    def created_by(self):
        """
        The user who created this object.

        Retrieves the user on the (one and only) creation HistoricalRecord for
        an instance.
        """
        try:
            return self.history.get(history_type='+').history_user
        except ObjectDoesNotExist:
            if self.created_by_fm:
                return self.created_by_fm
            else:
                try:
                    return self.history.order_by('modified_on')[0].history_user
                except:
                    return None

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

    dataset_literal = models.CharField(max_length=255, blank=True, null=True)
    # CHECK: Had to add on_delete so chose cascade -> JD: deleting of a datasets should not delete the object
    belongs_to = models.ForeignKey('Dataset', null=True, on_delete=models.SET_NULL)
    # CHECK: Had to add on_delete so chose cascade -> JD: same as above
    zotero_accession = models.ForeignKey('zotero.ImportAccession', blank=True, null=True, on_delete=models.SET_NULL)

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

    class Meta(object):
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
        return urllib.parse.urlunparse(('http', settings.DOMAIN,
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
        return super(ReferencedEntity, self).save(*args, **kwargs)


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

    def __str__(self):
        return self.name


class Citation(ReferencedEntity, CuratedMixin):
    """
    A bibliographic record.
    """
    ID_PREFIX = 'CBB'

    history = HistoricalRecords()

    # Allowing blank values is not ideal, but many existing records lack titles.
    title = models.CharField(max_length=2000, blank=True,
                             help_text="The name to be used to identify the"
                             " resource. For reviews that traditionally have no"
                             " title, this should be added as something like"
                             " '[Review of Title (Year) by Author]'.")

    title_for_sort = models.CharField(max_length=2000, blank=True, null=True,
                                      db_index=True)
    """ASCII-normalized title."""

    title_for_display = models.CharField(max_length=2000, blank=True, null=True)

    additional_titles = models.TextField(blank=True, null=True,
                                         help_text="Additional titles (not"
                                         " delimited, free text).")
    book_series = models.CharField(max_length=255, blank=True, null=True,
                                   help_text="Used for books, and potentially"
                                   " other works in a series.")

    created_native = models.DateTimeField(blank=True, null=True)
    # CHECK: Had to add on_delete so chose cascade -> JD: deleting user shouldn't delete citation
    created_by_native = models.ForeignKey(User, null=True, blank=True,
                                    help_text=help_text("""
    The user who created this object."""), related_name="creator_of", on_delete=models.SET_NULL)

    # CHECK: Had to add on_delete so chose cascade -> JD: deleting subtype shouldn't delete citation
    subtype = models.ForeignKey('CitationSubtype', blank=True, null=True, on_delete=models.SET_NULL)

    complete_citation =  models.TextField(blank=True, null=True,
                                         help_text="A complete citation that can be used to show a record if detailed information has not been entered yet.")

    STUB_RECORD = 'SR'
    REGULAR_RECORD = 'RR'
    RECORD_STATUS_CHOICES = (
        (STUB_RECORD, 'Stub Record'),
        (REGULAR_RECORD, 'Regular Record')
    )
    stub_record_status = models.CharField(max_length=3, null=True, blank=True,
                                       choices=RECORD_STATUS_CHOICES)

    def save(self, *args, **kwargs):
        def get_related(obj):
            query = Q(subject_id=obj.id) | Q(object_id=obj.id) & (Q(type_controlled='RO') | Q(type_controlled='RB'))
            return CCRelation.objects.filter(query)

        def get_title(obj):
            if obj.title:
                return obj.title
            else:
                title_parts = []
                for relation in get_related(obj):
                    if relation.type_controlled =='RO' and relation.object and relation.object.title:
                        title_parts.append(relation.object.title)
                    if relation.type_controlled == 'RB' and relation.subject and relation.subject.title:
                        title_parts.append(relation.subject.title)
                return u' '.join(title_parts)

        def get_display_title(obj):
            if not obj:
                return u'No linked citation'
            if obj.title:
                return obj.title
            relation = obj.ccrelations.select_related('subject', 'object')\
                .filter(type_controlled__in=['RO', 'RB'])\
                .values('subject_id', 'subject__title', 'object__title')
            if relation.count() > 0:
                relation = relation.first()
            else:
                relation = None
            if relation:
                if relation['subject__title'] or relation['object__title']:
                    return u'Review: %s' % relation['subject__title'] if relation['subject_id'] != obj.id else relation['object__title']
                else:
                    return u'(no title)'

            # IEXP-300: if there is no title but complete citation, show it instead
            if obj.complete_citation:
                return obj.complete_citation

            return u'Untitled review'

        if self.created_native is None:
            try:
                self.created_native = self.created_on
            except HistoricalCitation.DoesNotExist:
                pass

        # fixing issue with simple history where hisotyr user is not saved
        if not self.id:
            if hasattr(HistoricalRecords.thread, 'request'):
                if HistoricalRecords.thread.request.user:
                    self.created_by_native = HistoricalRecords.thread.request.user

        self.title_for_sort = normalize(unidecode.unidecode(get_title(self)))
        self.title_for_display = get_display_title(self)
        self.set_tracking_state()

        super(Citation, self).save(*args, **kwargs)

    def set_tracking_state(self):
        ratings = {
            Tracking.HSTM_UPLOAD: -1,
            Tracking.FULLY_ENTERED: 0,
            Tracking.PROOFED: 1,
            Tracking.AUTHORIZED: 2,
            Tracking.PRINTED: 3,
        }

        entries = [x.type_controlled for x in self.tracking_records.all()]
        sorted_entries = sorted(entries, key=lambda x: ratings[x] if x and x in ratings else -1, reverse=True)
        current_state = None
        if sorted_entries:
            current_state = sorted_entries[0]
        is_hstm = (Tracking.HSTM_UPLOAD in entries)

        tracking_mapping = {
            Citation.HSTM_UPLOAD: Tracking.HSTM_UPLOAD,
            Citation.PRINTED: Tracking.PRINTED,
            Citation.AUTHORIZED: Tracking.AUTHORIZED,
            Citation.PROOFED: Tracking.PROOFED,
            Citation.FULLY_ENTERED: Tracking.FULLY_ENTERED,
            None: None
        }

        self.tracking_state = tracking_mapping[current_state]
        self.hstm_uploaded = Citation.IS_HSTM_UPLOADED if is_hstm else None

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
    def human_readable_abstract(self):
        """
        Abstract stripped of html tags and other metadata tags
        """
        SAFE_TAGS = ['em', 'b', 'i', 'strong', 'a']
        SAFE_ATTRS = {'a': ['href', 'rel']}

        no_tags = mark_safe(bleach.clean(self.abstract, tags=SAFE_TAGS, # Whitelist
                                      attributes=SAFE_ATTRS,
                                      strip=True))
        match = re.search('\{AbstractBegin\}([\w\s\W\S]*)\{AbstractEnd\}', self.abstract)
        if match:
            return match.groups()[0].strip()
        return self.abstract

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
    WEB_OBJECT = 'WO'
    MULTIMEDIA_OBJECT = 'MO'
    ARCHIVE_OBJECT = 'AO'
    DIGITAL_RESOURCE = 'DR'
    PERSONAL_RECOGNITION = 'PC'

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
        (WEB_OBJECT, 'Web Object'),
        (MULTIMEDIA_OBJECT, 'Multimedia Object'),
        (ARCHIVE_OBJECT, 'Archive Object'),
        (DIGITAL_RESOURCE, 'Digital Resource'),
        (PERSONAL_RECOGNITION, 'Personal Recognition'),
    )
    type_controlled = models.CharField(max_length=2, null=True, blank=True,
                                       verbose_name='type',
                                       choices=TYPE_CHOICES,
                                       help_text=help_text("""
    This list can be extended to the resource types specified by Doublin Core
    Recource Types http://dublincore.org/documents/resource-typelist/
    """))

    HSTM_UPLOAD = 'HS'
    PRINTED = 'PT'
    AUTHORIZED = 'AU'
    PROOFED = 'PD'
    FULLY_ENTERED = 'FU'
    NONE = 'NO'
    TRACKING_CHOICES = (
        (HSTM_UPLOAD, 'HSTM Upload'),
        (PRINTED, 'Printed'),
        (AUTHORIZED, 'Authorized'),
        (PROOFED, 'Proofed'),
        (FULLY_ENTERED, 'Fully Entered'),
        (NONE, 'None')
    )
    tracking_state = models.CharField(max_length=2, null=True, blank=True,
                                      choices=TRACKING_CHOICES, db_index=True)
    """The current state of the record."""

    IS_HSTM_UPLOADED = "HS"
    HSTM_UPLOAD_CHOICES = (
        (IS_HSTM_UPLOADED, "HSTM Upload"),
    )
    hstm_uploaded = models.CharField(max_length=2, null=True, blank=True,
                                      choices=HSTM_UPLOAD_CHOICES)

    abstract = models.TextField(blank=True, null=True, help_text=help_text("""
    Abstract or detailed summaries of a work.
    """))

    edition_details = models.TextField(blank=True, null=True, help_text=help_text("""
    Use for describing the edition or version of the resource. Include names of
    additional contributors if necessary for clarification (such as translators,
    introduction by, etc). Always, use relationship table to list contributors
    (even if they are specified here).
    """))

    physical_details = models.CharField(max_length=255, null=True, blank=True,
                                        help_text=help_text("""
    For describing the physical description of the resource. Use whatever
    information is appropriate for the type of resource.
    """))

    # Storing this in the model would be kind of hacky. This will make it easier
    #  to do things like sort or filter by language.
    language = models.ManyToManyField('Language', blank=True, null=True,
    help_text=help_text("""
    Language of the resource. Multiple languages can be specified.
    """))

    # TODO: This relation should be from PartDetails to Citation, to support
    #  inlines in the Admin.

    # CHECK: Had to add on_delete so chose cascade -> JD: deleting partdetails shouldn't delete citation
    part_details = models.OneToOneField('PartDetails', null=True, blank=True,
                                        help_text=help_text("""
    New field: contains volume, issue, page information for works that are parts
    of larger works.
    """), on_delete=models.SET_NULL)

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

    resolutions = GenericRelation('zotero.InstanceResolutionEvent',
                                  related_query_name='citation_resolutions',
                                  content_type_field='to_model',
                                  object_id_field='to_instance_id')

    @property
    def linkeddata_public(self):
        return LinkedData.objects.filter(subject_instance_id=self.pk).filter(public=True)

    def __unicode__(self):
        return strip_tags(self.title)

    def __str__(self):
        return strip_tags(self.title)

    @property
    def ccrelations(self):
        """
        Provides access to related :class:`.CCRelation` instances directly.
        """
        query = Q(subject_id=self.id) | Q(object_id=self.id)
        return CCRelation.objects.filter(public=True).filter(query)

    @property
    def all_ccrelations(self):
        query = Q(subject_id=self.id) | Q(object_id=self.id)
        return CCRelation.objects.filter(query)


    @property
    def acrelations(self):
        """
        Provides access to related :class:`.ACRelation` instances directly.
        """
        query = Q(citation_id=self.id)
        return ACRelation.objects.filter(public=True).filter(query)

    @property
    def all_acrelations(self):
        query = Q(citation_id=self.id)
        return ACRelation.objects.filter(query)

    @property
    def get_all_contributors(self):
        query = Q(citation_id=self.id) & Q(type_broad_controlled__in=['PR'], data_display_order__lt=30)
        return ACRelation.objects.filter(public=True).filter(query).order_by('data_display_order')

    def get_absolute_url(self):
        """
        The absolute URL of a Citation is the citation detail view.
        """
        return core_reverse("citation", args=(self.id,))

class CitationSubtype(models.Model):

    name = models.CharField(max_length=1000, db_index=True, help_text=help_text("""
    Name of the new subtype.
    """))

    unique_name = models.CharField(max_length=1000, db_index=True, help_text=help_text("""
    Unique name of a subtype, use to reference a subtype.
    """))

    description = models.TextField(blank=True, null=True,
                                   help_text=help_text("""
    A brief description that will be displayed to help identify the authority.
    Such as, brief bio or a scope note. For classification terms will be text
    like 'Classification term from the XXX classification schema.'
    """))

    related_citation_type = models.CharField(max_length=2, null=True, blank=True,
                                       verbose_name='citation type',
                                       choices=Citation.TYPE_CHOICES,
                                       help_text=help_text("""
    Type of which this object is a subtype, e.g. Review or Chapter.
    """))

    def __str__(self):
        return self.name if self.name else 'Subtype'


class Authority(ReferencedEntity, CuratedMixin):
    ID_PREFIX = 'CBA'

    class Meta(object):
        verbose_name_plural = 'authority records'
        verbose_name = 'authority record'

    history = HistoricalRecords()

    name = models.CharField(max_length=1000, db_index=True, help_text=help_text("""
    Name, title, or other main term for the authority as will be displayed.
    """))

    name_for_sort = models.CharField(max_length=2000,  db_index=True, blank=True, null=True)
    """ASCII-normalized name."""

    created_on_stored = models.DateTimeField(blank=True, null=True)
    # CHECK: Had to add on_delete so chose cascade -> JD: deleting users shoulnd't delete authority
    created_by_stored = models.ForeignKey(User, null=True, blank=True,
                                    help_text=help_text("""
    The user who created this object."""), related_name="creator_of_object", on_delete=models.SET_NULL)


    def save(self, *args, **kwargs):
        self.name_for_sort = normalize(unidecode.unidecode(self.name))

        if not self.created_on_stored:
            try:
                self.created_on_stored = self.created_on
            except HistoricalCitation.DoesNotExist:
                pass

        super(Authority, self).save(*args, **kwargs)

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
    BIBLIOGRAPHIC_LIST = 'BL'
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
        (BIBLIOGRAPHIC_LIST, 'Bibliographic List')
    )
    type_controlled = models.CharField(max_length=2, null=True, blank=True,
                                       choices=TYPE_CHOICES,
                                       verbose_name="type",
                                       db_index=True,
                                       help_text=help_text("""
    Specifies authority type. Each authority thema has its own list of
    controlled type vocabulary.
    """))

    HSTM_UPLOAD = 'HS'
    PRINTED = 'PT'
    AUTHORIZED = 'AU'
    PROOFED = 'PD'
    FULLY_ENTERED = 'FU'
    BULK_DATA = 'BD'
    NONE = 'NO'
    TRACKING_CHOICES = (
        (HSTM_UPLOAD, 'HSTM Upload'),
        (PRINTED, 'Printed'),
        (AUTHORIZED, 'Authorized'),
        (PROOFED, 'Proofed'),
        (FULLY_ENTERED, 'Fully Entered'),
        (BULK_DATA, 'Bulk Data Update'),
        (NONE, 'No')
    )
    tracking_state = models.CharField(max_length=2, null=True, blank=True, db_index=True,
                                      choices=TRACKING_CHOICES)
    """The current state of the record."""

    SPWT = 'SPWT'
    SPWC = 'SPWC'
    NEU = 'NEU'
    MW = 'MW'
    SHOT = 'SHOT'
    SEARCH = 'SAC'
    PROPER_NAME = 'PN'
    GUE = 'GUE'
    FHSA = 'FHSA'
    CLASS_SYSTEM_CHOICES = (
        (SPWT, 'Weldon Thesaurus Terms (2002-present)'),
        (SPWC, 'Weldon Classification System (2002-present)'),
        (GUE, 'Guerlac Committee Classification System (1953-2001)'),
        (NEU, 'Neu'),
        (MW, 'Whitrow Classification System (1913-1999)'),
        (SHOT, 'SHOT Thesaurus Terms'),
        (FHSA, 'Forum for the History of Science in America'),
        (SEARCH, 'Search App Concept'),
        (PROPER_NAME, 'Proper name')
    )
    classification_system = models.CharField(max_length=4, blank=True,
                                             null=True, default=SPWC,
                                             choices=CLASS_SYSTEM_CHOICES,
                                             db_index=True,
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
    """), db_index=True)

    classification_hierarchy = models.CharField(max_length=255, blank=True,
                                                null=True,
                                                help_text=help_text("""
    Used for Classification Terms to describe where they fall in the
    hierarchy.
    """), db_index=True)

    # TODO: we need to remove this; it conflicts with CuratedMixin.
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

    # CHECK: Had to add on_delete so chose cascade -> JD: if redirected authority is delete this shouldn't be deleted
    redirect_to = models.ForeignKey('Authority', blank=True, null=True, on_delete=models.SET_NULL)

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



    @property
    def linkeddata_public(self):
        return LinkedData.objects.filter(subject_instance_id=self.pk).filter(public=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    @property
    def aarelations(self):
        """
        Provides access to related :class:`.AARelation` instances directly.
        """
        query = Q(subject_id=self.id) | Q(object_id=self.id)
        return AARelation.objects.filter(public=True).filter(query)

    @property
    def aarelations_all(self):
        """
        Provides access to related :class:`.AARelation` instances directly.
        """
        query = Q(subject_id=self.id) | Q(object_id=self.id)
        return AARelation.objects.filter(query)

    @property
    def acrelations(self):
        """
        Provides access to related :class:`.ACRelation` instances directly.
        """
        query = Q(authority_id=self.id)
        return ACRelation.objects.filter(public=True).filter(query)

    def get_absolute_url(self):
        """
        The absolute URL of an Authority is the authority detail view.
        """
        return core_reverse("authority", args=(self.id,))


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
    personal_name_last = models.CharField(max_length=255, blank=True)
    personal_name_first = models.CharField(max_length=255, blank=True)
    personal_name_suffix = models.CharField(max_length=255, blank=True)
    personal_name_preferred = models.CharField(max_length=255, blank=True)


class ACRelation(ReferencedEntity, CuratedMixin):
    """
    A relation between a :class:`.Authority` and a :class:`.Citaton`\.

    For example, between a paper and its author(s), a book and its place of
    publication, etc.
    """
    ID_PREFIX = 'ACR'

    class Meta(object):
        verbose_name = 'authority-citation relationship'
        verbose_name_plural = 'authority-citation relationships'

    history = HistoricalRecords()

    # CHECK: Had to add on_delete so chose cascade -> JD: ACRelations shouldn't be deleted when citations/authorities are
    citation = models.ForeignKey('Citation', blank=True, null=True, on_delete=models.SET_NULL)

    # CHECK: Had to add on_delete so chose cascade -> JD: ACRelations shouldn't be deleted when citations/authorities are
    authority = models.ForeignKey('Authority', blank=True, null=True, on_delete=models.SET_NULL)

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
    COMMITTEE_MEMBER = 'CM'

    # New types for IEXP-15
    ORGANIZER = 'OR'
    INTERVIEWER = 'IV'
    GUEST = 'GU'
    CREATOR = 'CR'
    PRODUCER = 'PR'
    DIRECTOR = 'DI'
    WRITER = 'WR'
    PERFORMER = 'PF'
    COLLECTOR = 'CL'
    ARCHIVIST = 'AR'
    RESEARCHER = 'RE'
    DEVELOPER = 'DE'
    COMPILER = 'CP'
    AWARDEE = 'AW'
    OFFICER = 'OF'
    HOST = 'HO'
    DISTRIBUTOR = 'DS'
    ARCHIVAL_REPOSITORY = 'AC'
    MAINTAINING_INSTITUTION = 'MI'
    PRESENTING_GROUP = 'PG'

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
        (BOOK_SERIES, 'Book Series'),
        (COMMITTEE_MEMBER, 'Committee Member'),
        (ORGANIZER, 'Organizer'),
        (INTERVIEWER, 'Interviewer'),
        (GUEST, 'Guest'),
        (CREATOR, 'Creator'),
        (PRODUCER, 'Producer'),
        (DIRECTOR, 'Director'),
        (WRITER, 'Writer'),
        (PERFORMER, 'Performer'),
        (COLLECTOR, 'Collector'),
        (ARCHIVIST, 'Archivist'),
        (RESEARCHER, 'Researcher'),
        (DEVELOPER, 'Developer'),
        (COMPILER, 'Compiler'),
        (AWARDEE, 'Awardee'),
        (OFFICER, 'Officer'),
        (HOST, 'Host'),
        (DISTRIBUTOR, 'Distributor'),
        (ARCHIVAL_REPOSITORY, 'Archival Repository'),
        (MAINTAINING_INSTITUTION, 'Maintaining Institution'),
        (PRESENTING_GROUP, 'Presenting Group'),
    )
    type_controlled = models.CharField(max_length=2, null=True, blank=True,
                                       choices=TYPE_CHOICES,
                                       verbose_name='relationship type',
                                       help_text=help_text("""
    Used to specify the nature of the relationship between authority (as the
    subject) and the citation (as the object).
    """))

    TYPE_CATEGORY_PUB_DISTR = [PUBLISHER, SCHOOL, PERIODICAL, HOST, DISTRIBUTOR, ARCHIVAL_REPOSITORY, MAINTAINING_INSTITUTION, PRESENTING_GROUP]

    PERSONAL_RESPONS_TYPES = [AUTHOR, EDITOR, ADVISOR, COMMITTEE_MEMBER, CONTRIBUTOR, TRANSLATOR,
        ORGANIZER, INTERVIEWER, GUEST, CREATOR, PRODUCER, DIRECTOR,
        WRITER, PERFORMER, COLLECTOR, ARCHIVIST, RESEARCHER, DEVELOPER,
        COMPILER, AWARDEE, OFFICER]
    SUBJECT_CONTENT_TYPES = [SUBJECT, CATEGORY]
    INSTITUTIONAL_HOST_TYPES = [PUBLISHER, SCHOOL, INSTITUTION]
    PUBLICATION_HOST_TYPES = [PERIODICAL, BOOK_SERIES]


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
                                             blank=True, null=True,
                                             verbose_name='relationship type (broad)',
                                             help_text=help_text("""
    Used to specify the nature of the relationship between authority (as the
    subject) and the citation (as the object) more broadly than the relationship
    type.
    """))

    RESPONSIBILITY_MAPPING = {
        Citation.BOOK: [AUTHOR, EDITOR],
        Citation.ARTICLE: [AUTHOR],
        Citation.CHAPTER: [AUTHOR],
        Citation.REVIEW: [AUTHOR],
        Citation.ESSAY_REVIEW: [AUTHOR],
        Citation.THESIS: [AUTHOR, ADVISOR, COMMITTEE_MEMBER],
        Citation.EVENT: [AUTHOR, ORGANIZER],
        Citation.WEB_OBJECT: [AUTHOR, INTERVIEWER, GUEST, CREATOR],
        Citation.MULTIMEDIA_OBJECT: [PRODUCER, DIRECTOR, WRITER, PERFORMER, CREATOR],
        Citation.ARCHIVE_OBJECT: [COLLECTOR, ARCHIVIST, RESEARCHER, AUTHOR],
        Citation.DIGITAL_RESOURCE: [DEVELOPER, WRITER, COMPILER, EDITOR],
        Citation.PERSONAL_RECOGNITION: [AWARDEE, OFFICER],
    }

    HOST_MAPPING = {
        Citation.BOOK: [PUBLISHER],
        Citation.ARTICLE: [PERIODICAL],
        Citation.CHAPTER: [PUBLISHER],
        Citation.REVIEW: [PERIODICAL],
        Citation.ESSAY_REVIEW: [PERIODICAL],
        Citation.THESIS: [SCHOOL],
        Citation.EVENT: [HOST],
        Citation.WEB_OBJECT: [PUBLISHER, DISTRIBUTOR, HOST],
        Citation.MULTIMEDIA_OBJECT: [PUBLISHER, DISTRIBUTOR],
        Citation.ARCHIVE_OBJECT: [ARCHIVAL_REPOSITORY],
        Citation.DIGITAL_RESOURCE: [MAINTAINING_INSTITUTION],
        Citation.PERSONAL_RECOGNITION: [PRESENTING_GROUP],
    }

    type_free = models.CharField(max_length=255,
                                 blank=True,
                                 verbose_name="relationship type (free-text)",
                                 help_text="""
    Free-text description of the role that the authority plays in the
    citation (e.g. 'introduction by', 'dissertation supervisor', etc).
    """)

    name_for_display_in_citation = models.CharField(max_length=255, blank=True,
                                                    null=True,
                                                    help_text=help_text("""
    Display for the authority as it is to be used when being displayed with the
    citation. Eg. the form of the author's name as it appears on a
    publication--say, J.E. Koval--which might be different from the name of the
    authority--Jenifer Elizabeth Koval.
    """))

    name_as_entered = models.CharField(max_length=255, null=True, blank=True,
                                       help_text=help_text("""
    Display for the authority as it is has been used in a publication.
    """))

    personal_name_first = models.CharField(max_length=255, null=True, blank=True)
    personal_name_last = models.CharField(max_length=255, null=True, blank=True)
    personal_name_suffix = models.CharField(max_length=255, null=True, blank=True)

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

    resolutions = GenericRelation('zotero.InstanceResolutionEvent',
                                  related_query_name='acrelation_resolutions',
                                  content_type_field='to_model',
                                  object_id_field='to_instance_id')

    def _render_type_controlled(self):
        try:
            return dict(self.TYPE_CHOICES)[self.type_controlled]
        except KeyError:
            return u'None'

    def __unicode__(self):
        values = (self.citation, self._render_type_controlled(), self.authority)
        return u'{0} - {1} - {2}'.format(*values)

    def __str__(self):
        values = (self.citation, self._render_type_controlled(), self.authority)
        return u'{0} - {1} - {2}'.format(*values)

    def save(self, *args, **kwargs):
        if self.type_controlled is not None:
            if self.type_controlled in self.PERSONAL_RESPONS_TYPES:
                self.type_broad_controlled = self.PERSONAL_RESPONS
            elif self.type_controlled in self.SUBJECT_CONTENT_TYPES:
                self.type_broad_controlled = self.SUBJECT_CONTENT
            elif self.type_controlled in self.INSTITUTIONAL_HOST_TYPES:
                self.type_broad_controlled = self.INSTITUTIONAL_HOST
            elif self.type_controlled in self.PUBLICATION_HOST_TYPES:
                self.type_broad_controlled = self.PUBLICATION_HOST

        # Trigger indexing of Authority and Citation instances.
        # ISISCB-1047: first the ACRelation needs to be saved so that the corrected data
        # is being indexed when saving the authority and citation objects
        super(ACRelation, self).save(*args, **kwargs)
        if self.authority:
            self.authority.save()
        if self.citation:
            self.citation.save()

class AARSet(ReferencedEntity, CuratedMixin):

    ID_PREFIX = 'AARSET'

    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class AARelationType(ReferencedEntity, CuratedMixin):
    ID_PREFIX = 'AARTYPE'

    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    aarset = models.ForeignKey(AARSet, related_name='relation_types', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    TYPE_STRUCTURAL = "TSTR"
    TYPE_ONTOLOGICAL = "TONT"
    TYPE_TEMPORAL = "TTEM"
    TYPE_GEOGRAPHICAL = "TGEO"

    RELATION_TYPE_CHOICES =  (
        (TYPE_STRUCTURAL, "Structural"),
        (TYPE_ONTOLOGICAL, "Ontological"),
        (TYPE_TEMPORAL, "Temporal"),
        (TYPE_GEOGRAPHICAL, "Geographical")
    )
    relation_type_controlled = models.CharField(max_length=4, choices=RELATION_TYPE_CHOICES,
                                       null=True, blank=True,
                                       help_text=help_text("""
    The type of the relationship.
    """))

    IDENTICAL_TO = 'IDTO'
    PARENT_OF = 'PAOF'
    #PREVIOUS_TO = 'PRETO'
    #OFFICER_OF = 'OFOF'
    ASSOCIATED_WITH = 'ASWI'
    TYPE_CHOICES = (
        (IDENTICAL_TO, 'Is Identical To'),
        (PARENT_OF, 'Is Parent Of'),
        #(PREVIOUS_TO, 'Happened Previous To'),
        #(OFFICER_OF, 'Is Officer Of'),
        (ASSOCIATED_WITH, 'Is Associated With')
    )
    base_type = models.CharField(max_length=5, choices=TYPE_CHOICES,
                                       null=True, blank=True,
                                       help_text=help_text("""
    The base type the new relationship type can be mapped to.
    """))

class AARelation(ReferencedEntity, CuratedMixin):
    """
    A relation between two :class:`.Authority` instances.

    For example, between a teacher and a student, an employee and an
    instutution, between two events, etc.
    """
    ID_PREFIX = 'AAR'

    class Meta(object):
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
        #(PREVIOUS_TO, 'Happened Previous To'),
        #(OFFICER_OF, 'Is Officer Of'),
        (ASSOCIATED_WITH, 'Is Associated With')
    )
    type_controlled = models.CharField(max_length=5, choices=TYPE_CHOICES,
                                       null=True, blank=True,
                                       help_text=help_text("""
    Controlled term specifying the nature of the relationship
    (the predicate between the subject and object).
    """))

    aar_type = models.ForeignKey(AARelationType, null=True, on_delete=models.SET_NULL)

    type_free = models.CharField(max_length=255, blank=True,
                                 help_text=help_text("""
    Free text description of the relationship.
    """))

    # CHECK: Had to add on_delete so chose cascade -> JD: AARel shouldn't be deleted when subject/object are
    subject = models.ForeignKey('Authority', related_name='relations_from', on_delete=models.SET_NULL, null=True)

    # CHECK: Had to add on_delete so chose cascade -> JD: AARel shouldn't be deleted when subject/object are
    object = models.ForeignKey('Authority', related_name='relations_to', on_delete=models.SET_NULL, null=True)

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


    def _render_type_controlled(self):
        try:
            return dict(self.TYPE_CHOICES)[self.type_controlled]
        except KeyError:
            return u'None'


    def __unicode__(self):
        values = (self.subject, self._render_type_controlled(), self.object)
        return u'{0} - {1} - {2}'.format(*values)

    def __str__(self):
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

    class Meta(object):
        verbose_name = 'citation-citation relationship'
        verbose_name_plural = 'citation-citation relationships'

    history = HistoricalRecords()

    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    INCLUDES_CHAPTER = 'IC'
    INCLUDES_SERIES_ARTICLE = 'ISA'
    INCLUDES_CITATION_OBJECT = 'ICO'
    REVIEW_OF = 'RO'
    REVIEWED_BY = 'RB'
    RESPONDS_TO = 'RE'
    ASSOCIATED_WITH = 'AS'
    TYPE_CHOICES = (
        (INCLUDES_CHAPTER, 'Includes Chapter'),
        (INCLUDES_SERIES_ARTICLE, 'Includes Series Article'),
        (INCLUDES_CITATION_OBJECT, 'Includes'),
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

    # CHECK: Had to add on_delete so chose cascade -> JD: CCREL shouldn't be deleted when citations are
    subject = models.ForeignKey('Citation', related_name='relations_from', null=True, blank=True, on_delete=models.SET_NULL)

    # CHECK: Had to add on_delete so chose cascade -> JD: CCREL shouldn't be deleted when citations are
    object = models.ForeignKey('Citation', related_name='relations_to', null=True, blank=True, on_delete=models.SET_NULL)

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

    data_display_order = models.FloatField(default=1.0, help_text=help_text("""
    Position at which the citation should be displayed in the citation detail
    view. Whole numbers or decimals can be used.
    """))

    def _render_type_controlled(self):
        try:
            return dict(self.TYPE_CHOICES)[self.type_controlled]
        except KeyError:
            return u'None'


    def __unicode__(self):
        values = (self.subject, self._render_type_controlled(), self.object)
        return u'{0} - {1} - {2}'.format(*values)

    def __str__(self):
        values = (self.subject, self._render_type_controlled(), self.object)
        return u'{0} - {1} - {2}'.format(*values)

    def save(self, *args, **kwargs):
        super(CCRelation, self).save(*args, **kwargs)
        # Trigger indexing of Authority and Citation instances.
        if self.subject:
            self.subject.save()
        if self.object:
            self.object.save()


class LinkedDataType(models.Model):
    class Meta(object):
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

            raise ValidationError(message)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name


class AttributeType(models.Model):
    name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255, blank=True, null=True,
                                    help_text=help_text("""
    The "name" attribute is not always suitable for display in public views.
    This field provides the name to be displayed to users.
    """))

    # CHECK: Had to add on_delete so chose cascade -> JD: can't be null, so cascade
    value_content_type = models.ForeignKey(ContentType,
                                           limit_choices_to=VALUETYPES,
                                           related_name='attribute_value', on_delete=models.CASCADE)

    attribute_help_text = models.TextField(default=None, null=True, blank=True, help_text=help_text("""
    The help text the user sees when adding a new attribute of this type.
    """))

    def __unicode__(self):
        return u'{0} ({1})'.format(self.name, self.value_content_type.model)

    def __str__(self):
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

    # CHECK: Had to add on_delete so chose cascade -> JD: can't be null, so cascade
    # Generic relation.
    source_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    source_instance_id = models.CharField(max_length=200)
    source = GenericForeignKey('source_content_type', 'source_instance_id')

    # The selected AttributeType determines the type of Value (i.e. Value
    #  subclass) that can be related to this Attribute.
    # CHECK: Had to add on_delete so chose cascade -> JD: can't be null, so cascade
    type_controlled = models.ForeignKey('AttributeType', verbose_name='type',
                                        help_text=help_text("""
    The "type" field determines what kinds of values are acceptable for this
    attribute.
    """), on_delete=models.CASCADE)

    # TODO: Instead of saving this in the Attribute model, we may want to create
    #  a mechanism for grouping/ranking AttributeTypes.
    type_controlled_broad = models.CharField(max_length=255, blank=True)
    type_free = models.CharField(max_length=255, blank=True)

    BEGIN = 'BGN'
    END = 'END'
    OCCUR = 'OCR'
    QUALIFIER_CHOICES = (
        (BEGIN, 'Began'),
        (END, 'Ended'),
        (OCCUR, 'Occurred'),
    )
    type_qualifier = models.CharField(max_length=3, choices=QUALIFIER_CHOICES,
                                      blank=True, null=True)

    def __unicode__(self):
        try:
            return u'{0}: {1}'.format(self.type_controlled.name,
                                      self.value.cvalue())
        except:
            return u''

    def __str__(self):
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

    class Meta(object):
        verbose_name = 'part detail'
        verbose_name_plural = 'part details'


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

    sort_order = models.IntegerField(default=0, help_text=help_text(""""
    New field: provides a sort order for works that are part of a larger work.
    """))

    extent = models.PositiveIntegerField(blank=True, null=True,
                                         help_text=help_text("""
    Provides the size of the work in pages, words, or other counters."""))
    extent_note = models.TextField(blank=True, null=True)

    @property
    def pages(self):
        if not self.page_end and self.pages_free_text:
            return self.pages_free_text

        if self.page_begin and self.page_end:
            return u'{0} - {1}'.format(self.page_begin, self.page_end)

        return self.page_begin if self.page_begin else self.page_end

class Place(models.Model):
    """
    A concept of locality associated with a particular point or region in space.
    """
    name = models.CharField(max_length=255)
    # CHECK: Had to add on_delete so chose cascade -> JD: probably not (I don't think we use this at the moment)
    gis_location = models.ForeignKey('Location', blank=True, null=True, on_delete=models.SET_NULL)
    # CHECK: Had to add on_delete so chose cascade -> JD: probably not (I don't think we use this at the moment)
    gis_schema = models.ForeignKey('LocationSchema', blank=True, null=True, on_delete=models.SET_NULL)


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

    class Meta(object):
        verbose_name = 'linked data entry'
        verbose_name_plural = 'linked data entries'

    history = HistoricalRecords()

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

    # In the Admin, we should limit the queryset to Authority and Citation
    #  instances only.
    # CHECK: Had to add on_delete so chose cascade -> JD: probably fine (should never happen though so far)
    subject_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    subject_instance_id = models.CharField(max_length=200)
    subject = GenericForeignKey('subject_content_type',
                                'subject_instance_id')

    # CHECK: Had to add on_delete so chose cascade -> JD: probably not (should also never happen)
    type_controlled = models.ForeignKey('LinkedDataType', verbose_name='type',
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


class AuthorityTracking(ReferencedEntity, CuratedMixin):
    """
    An audit entry for tracking the status of records in the curatorial process.

    This is a higher-level concept than the History audit log, which records
    only changes to entries.
    """
    ID_PREFIX = 'TRA'

    history = HistoricalRecords()

    tracking_info = models.CharField(max_length=255, blank=True)

    HSTM_UPLOAD = 'HS'
    PRINTED = 'PT'
    AUTHORIZED = 'AU'
    PROOFED = 'PD'
    FULLY_ENTERED = 'FU'
    BULK_DATA = 'BD'
    NONE = 'NO'
    TYPE_CHOICES = (
        (HSTM_UPLOAD, 'HSTM Upload'),
        (PRINTED, 'Printed'),
        (AUTHORIZED, 'Authorized'),
        (PROOFED, 'Proofed'),
        (FULLY_ENTERED, 'Fully Entered'),
        (BULK_DATA, 'Bulk Data Update'),
        (NONE, 'None')
    )

    type_controlled = models.CharField(max_length=2, null=True, blank=True,
                                       choices=TYPE_CHOICES, db_index=True)

    # CHECK: Had to add on_delete so chose cascade -> JD: yes, that makes sense,
    # if the authority no longer exists, tracking record doesn't need to either
    authority = models.ForeignKey(Authority, related_name='tracking_records',
                                  null=True, blank=True, on_delete=models.CASCADE)

    notes = models.TextField(blank=True)


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
    NONE = 'NO'
    TYPE_CHOICES = (
        (HSTM_UPLOAD, 'HSTM Upload'),
        (PRINTED, 'Printed'),
        (AUTHORIZED, 'Authorized'),
        (PROOFED, 'Proofed'),
        (FULLY_ENTERED, 'Fully Entered'),
        (BULK_DATA, 'Bulk Data Update'),
        (NONE, 'None'),
    )
    type_controlled = models.CharField(max_length=2, null=True, blank=True,
                                       choices=TYPE_CHOICES, db_index=True)

    # CHECK: Had to add on_delete so chose cascade -> JD: yes that makes sense.
    # if citation doesn't exist anymore, tracking record doesn't need to either
    citation = models.ForeignKey(Citation, related_name='tracking_records',
                                 null=True, blank=True, on_delete=models.CASCADE)

    notes = models.TextField(blank=True)


class Annotation(models.Model):
    """
    User-generated content associated with a specific entity.
    """
    # CHECK: Had to add on_delete so chose cascade -> JD: can't be null, so set it to cascade
    subject_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    subject_instance_id = models.CharField(max_length=200)
    subject = GenericForeignKey('subject_content_type',
                                'subject_instance_id')

    subject_field = models.CharField(max_length=255, blank=True, null=True,
                                     help_text=help_text("""
    The name of the field in ``subject`` to which this annotation refers. For
    example, ``title``.
    """))

    # CHECK: Had to add on_delete so chose cascade -> JD: I don't think we use this,
    # but if so, we probalby want to keep it when user is deleted.
    created_by = models.ForeignKey(User, related_name='annotations', null=True, on_delete=models.SET_NULL)
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


class CitationCollection(models.Model):
    """
    An arbitrary group of :class:`.Citation` instances.
    """

    name = models.CharField(max_length=255, blank=True, null=True)
    citations = models.ManyToManyField('Citation', related_name='in_collections')
    # CHECK: Had to add on_delete so chose cascade -> JD: we probably want to keep it around
    # (right now this is not possible I believe)
    createdBy = models.ForeignKey(User, related_name='citation_collections', on_delete=models.SET_NULL, null=True)
    created = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return '%s (%s)' % (self.name, self.createdBy.username)

    def __str__(self):
        return '%s (%s)' % (self.name, self.createdBy.username)

class AuthorityCollection(models.Model):
    """
    An arbitrary group of :class:`.Authority` instances.
    """

    name = models.CharField(max_length=255, blank=True, null=True)
    authorities = models.ManyToManyField('Authority', related_name='in_collections')
    # CHECK: Had to add on_delete so chose cascade -> JD: we probably want to keep it around
    # (right now this is not possible I believe)
    createdBy = models.ForeignKey(User, related_name='authority_collections', on_delete=models.SET_NULL, null=True)
    created = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return '%s (%s)' % (self.name, self.createdBy.username)

    def __str__(self):
        return '%s (%s)' % (self.name, self.createdBy.username)


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
        snip = self.text[:min(100, len(self.text))]
        if len(self.text) > 100:
            snip += u'...'
        return snip

    @property
    def linkified(self):
        return linkify(self.text)

    class Meta(object):
        get_latest_by = 'created_on'


class TagAppellation(Annotation):
    """
    The appellation of an entity with a :class:`.Tag`\.
    """
    # CHECK: Had to add on_delete so chose cascade -> JD: I don't think we use this
    # but let's keep it around
    tag = models.ForeignKey('Tag', on_delete=models.SET_NULL, null=True)


class Tag(models.Model):
    """
    An :class:`.Annotation` from a controlled vocabulary
    (:class:`.TaggingSchema`).
    """
    # CHECK: Had to add on_delete so chose cascade -> JD: same as above
    schema = models.ForeignKey('TaggingSchema', related_name='tags', on_delete=models.SET_NULL, null=True)
    value = models.CharField(max_length=255)
    description = models.TextField()

    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)


class TaggingSchema(models.Model):
    """
    A named set of :class:`.Tag`\s.
    """
    name = models.CharField(max_length=255)

    # CHECK: Had to add on_delete so chose cascade -> JD: same as above
    created_by = models.ForeignKey(User, related_name='tagging_schemas', on_delete=models.SET_NULL, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)


class SearchQuery(models.Model):
    # CHECK: Had to add on_delete so chose cascade -> JD: that should be fine
    user = models.ForeignKey(User, related_name='searches', on_delete=models.CASCADE)
    created_on = models.DateTimeField(auto_now_add=True)
    parameters = models.TextField()
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
    # CHECK: Had to add on_delete so chose cascade -> JD: that should be fine
    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)

    affiliation = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    bio = MarkupField(markup_type='markdown', blank=True, null=True)

    share_email = models.BooleanField(default=False, help_text=help_text("""
    A user can indicate whether or not their email address should be made
    public."""))

    # CHECK: Had to add on_delete so chose cascade -> JD: we want to keep the user profile
    # when the resolver has been deleted.
    resolver_institution = models.ForeignKey(Institution, blank=True, null=True,
                                             related_name='users',
                                             help_text=help_text("""
    A user can select an institution for which OpenURL links should be
    generated while searching."""), on_delete=models.SET_NULL)

    # CHECK: Had to add on_delete so chose cascade -> JD: user profile should be kept
    authority_record = models.OneToOneField(Authority, blank=True, null=True,
                                            related_name='associated_user',
                                            help_text=help_text("""
    A user can 'claim' an Authority record, asserting that the record refers to
    theirself."""), on_delete=models.SET_NULL)


# --------------------- cache objects -------------------------------

class CachedTimeline(models.Model):
    """
    Caches timeline data generated for authorities.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    authority_id = models.CharField(max_length=255, blank=True, null=True)
    complete = models.BooleanField(default=False)
    recalculate = models.BooleanField(default=False)


class CachedTimelineYear(models.Model):
    """
    Caches timeline data for one year.
    """
    year = models.IntegerField()

    # CHECK: Had to add on_delete so chose cascade -> JD: yes that makes sense
    timeline_year = models.ForeignKey(CachedTimeline, related_name='years', on_delete=models.CASCADE)

    book_count = models.BigIntegerField()
    thesis_count = models.BigIntegerField()
    chapter_count = models.BigIntegerField()
    article_count = models.BigIntegerField()
    review_count = models.BigIntegerField()
    other_count = models.BigIntegerField()


class CachedTimelineTitle(models.Model):
    """
    Caches timeline data for one title.
    """
    title = models.TextField()
    authors = models.TextField()
    # CHECK: Had to add on_delete so chose cascade -> JD: yes that makes sense, but Citations
    # can't be deleted at the moment
    citation = models.ForeignKey(Citation, blank=True, null=True, on_delete=models.CASCADE)

    # CHECK: Had to add on_delete so chose cascade -> JD: yes, that makes sense
    timeline_year = models.ForeignKey(CachedTimelineYear, related_name='titles', on_delete=models.CASCADE)
    citation_type = models.CharField(max_length=2, null=True, blank=True,
                                       verbose_name='type',
                                       choices=Citation.TYPE_CHOICES)

# ---------------------- Curation models ----------------------------


class IsisCBRole(models.Model):
    """
    Supports permission mechanism for IsisCB
    """
    name = models.CharField(max_length=255, blank=False, null=False)
    description = models.TextField(null=True, blank=True)

    users = models.ManyToManyField(User)

    @property
    def dataset_rules(self):
        return DatasetRule.objects.filter(role=self.pk)

    @property
    def crud_rules(self):
        return CRUDRule.objects.filter(role=self.pk)

    @property
    def field_rules(self):
        return FieldRule.objects.filter(role=self.pk)

    @property
    def user_module_rules(self):
        return UserModuleRule.objects.filter(role=self.pk)

    @property
    def zotero_rules(self):
        return ZoteroRule.objects.filter(role=self.pk)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name


class AccessRule(models.Model):
    """
    Parent class for all rules

    TODO: can we make this abstract? :-(
    """

    name = models.CharField(max_length=255, blank=True, null=True)

    # CHECK: Had to add on_delete so chose cascade -> JD: yes, I believe this makese sense
    role = models.ForeignKey(IsisCBRole, null=True, blank=True,
                             help_text=help_text("""The role a rules belongs to."""), on_delete=models.CASCADE)

    CITATION = 'citation'
    AUTHORITY = 'authority'
    OBJECT_TYPES = (
        (CITATION, 'Citation'),
        (AUTHORITY, 'Authority'),
    )
    object_type = models.CharField(max_length=255, null=True, blank=True,
                                       choices=OBJECT_TYPES)


class CRUDRule(AccessRule):
    """
    This rule defines a CRUD permission on all records, e.g. edit all records.
    """
    CREATE = 'create'
    VIEW = 'view'
    UPDATE = 'update'
    DELETE = 'delete'
    CRUD_CHOICES = (
        (CREATE, 'Create'),
        (VIEW, 'View'),
        (UPDATE, 'Update'),
        (DELETE, 'Delete'),
    )
    crud_action = models.CharField(max_length=255, null=False, blank=False,
                                   choices=CRUD_CHOICES)


class FieldRule(AccessRule):
    """
    This rule defines edit access to a specific field.
    """
    field_name = models.CharField(max_length=255, null=False, blank=False)

    CANNOT_VIEW = 'cannot_view'
    CANNOT_UPDATE = 'cannot_update'
    FIELD_CHOICES = (
        (CANNOT_VIEW, 'Cannot View'),
        (CANNOT_UPDATE, 'Cannot Update'),
    )
    field_action = models.CharField(max_length=255, null=False, blank=False, choices=FIELD_CHOICES)


class DatasetRule(AccessRule):
    """
    This rules limits the records a user has access to to a specific dataset.
    """
    dataset = models.CharField(max_length=255, null=True, blank=True, default=None)


class UserModuleRule(AccessRule):
    """
    This rule allows a user access to the user management module.
    """

    VIEW = 'view'
    UPDATE = 'update'
    FIELD_CHOICES = (
        (VIEW, 'View'),
        (UPDATE, 'Update'),
    )
    module_action = models.CharField(max_length=255, null=False, blank=False, choices=FIELD_CHOICES)


class ZoteroRule(AccessRule):
    """
    This rule allows a user access to the Zotero module.
    """
    # so far no properties


class Dataset(CuratedMixin):
    name = models.CharField(max_length=255)
    description = models.TextField()
    editor = models.CharField(max_length=255, null=True)

    def __unicode__(self):
        return u'{0}'.format(self.name)

    def __str__(self):
        return u'{0}'.format(self.name)


class AsyncTask(models.Model):
    """
    Represents an user-initiated asynchronous job, such as a bulk update.
    """

    async_uuid = models.CharField(max_length=255, blank=True, null=True)

    max_value = models.FloatField(default=0.0)
    current_value = models.FloatField(default=0.0)
    state = models.CharField(max_length=10, blank=True, null=True)
    label = models.TextField(default="")

    # CHECK: Had to add on_delete so chose cascade -> JD: we probably want to keep this around
    created_by = models.ForeignKey(User, related_name='tasks', null=True, on_delete=models.SET_NULL)
    created_on = models.DateTimeField(null=True)

    _value = models.TextField()
    """Use jsonpickle to serialize/deserialize return values."""

    def _get_value(self):
        return jsonpickle.decode(self._value)

    def _set_value(self, value):
        self._value = jsonpickle.encode(value)

    value = property(_get_value, _set_value)

    @property
    def progress(self):
        if self.max_value and self.max_value > 0:
            return 100.*self.current_value/self.max_value
        return 0.

    def save(self, *args, **kwargs):
        if not self.id:
            self.created_on = datetime.datetime.utcnow()
        return super(AsyncTask, self).save(*args, **kwargs)
