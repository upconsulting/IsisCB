from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist, FieldError, ValidationError
from django.contrib.contenttypes.models import ContentType
from isisdata.models import *

import datetime
import xml.etree.ElementTree as ET
import os
import copy
import json
import re
import pprint


def fast_iter(context, func, *extra):
    for event, e in context:
        func(e, *extra)
        # e.clear()
    del context


class FMPDSOParser(object):
    fm_namespace = '{http://www.filemaker.com/fmpdsoresult}'
    datetime_formats = [
        '%m/%d/%Y %I:%M:%S %p',
        '%m/%d/%Y %I:%M %p'
    ]
    date_formats = [
        '%m/%d/%Y',
        '%Y'
    ]
    chunk_size = 10000  # Number of instances to include in each fixture file.
    as_int = lambda x: int(x)
    as_upper = lambda x: x.upper()

    id_prefixes = {
        'CBB': 'citation',
        'CBA': 'authority',
        'ACR': 'acrelation',
        'AAR': 'aarelation',
        'CCR': 'ccrelation',
    }

    @staticmethod
    def _as_datetime(model_name, fm_field, fm_value):
        """
        Attempt to coerce a value to ``datetime``.
        """
        for format in FMPDSOParser.datetime_formats + FMPDSOParser.date_formats:
            try:
                return datetime.datetime.strptime(fm_value, format)
            except ValueError:
                pass
        raise ValueError('Could not coerce value to datetime: %s' % fm_value)

    @staticmethod
    def _to_int(model_name, fm_field, fm_value):
        try:
            return int(fm_value)
        except TypeError:
            return 1

    @staticmethod
    def _to_float(model_name, fm_field, fm_value):
        return float(fm_value)

    @staticmethod
    def _to_date(model_name, fm_field, fm_value):
        return FMPDSOParser._as_datetime(fm_value).date()

    @staticmethod
    def _try_int(model_name, fm_field, fm_value):
        print fm_field, fm_value
        try:
            return int(fm_value)
        except ValueError:
            return fm_value

    @staticmethod
    def _handle_record_status(model_name, fm_field, fm_value):

        if not fm_value:

            return True, 'Active', u'Set active by default'
        match = re.match('(In)?[aA]ctive(.*)', fm_value)
        if match:
            public_raw, explanation_raw = match.groups()
            public = False if public_raw else True
            explanation = explanation_raw.strip()
            status = 'Active' if public else 'Inactive'
        else:
            match = re.match('Redirect(.*)', fm_value)
            if match:
                explanation_raw = match.groups()[0].strip()
                public, status, explanation = False, 'Redirect', explanation_raw
            else:
                public, status, explanation = False, 'Inactive', u''
        return public, status, explanation

    @staticmethod
    def _handle_attribute_value(model_name, fm_field, fm_value):
        if fm_field == 'DateBegin':
            return (FMPDSOParser._to_int(fm_value), 'BGN')
        elif fm_field == 'DateEnd':
            return (FMPDSOParser._to_int(fm_value), 'END')

    fields = {
        'StaffNotes': 'administrator_notes',
        'RecordStatus': ('public', 'record_status_value', 'record_status_explanation'),
        'RecordHistory': 'record_history',
        'ID': 'id',
        'Dataset': 'dataset',
        'CreatedBy': 'created_by_fm',
        'CreatedOn': 'created_on_fm',
        'ModifiedBy': 'modified_by_fm',
        'ModifiedOn': 'modified_on_fm',
        'Description': 'description',
        'Name': 'name',
        'Type.free': 'type_free',
        'DataDisplayOrder': 'data_display_order',
        'ConfidenceMeasure': 'confidence_measure',
        'RelationshipWeight': 'relationship_weight',

        'citation': {
            'Abstract': 'abstract',
            'Title': 'title',
            'Type.controlled': 'type_controlled',
            'AdditionalTitles': 'additional_titles',
            'BookSeries': 'book_series',
            'EditionDetails': 'edition_details',
            'PhysicalDetails': 'physical_details',
            'RecordHistory': 'record_history',
            'NotesOnContent.notpublished': 'administrator_notes',
            'NotesOnProvenance': 'record_history',
            'Language': 'language',
        },
        'partdetails': {
            'IssueBegin': 'issue_begin',
            'IssueEnd': 'issue_end',
            'IssueFreeText': 'issue_free_text',
            'PageBegin': 'page_begin',
            'PageEnd': 'page_end',
            'PagesFreeText': 'pages_free_text',
            'VolumeEnd': 'volume_end',
            'VolumeBegin': 'volume_begin',
            'VolumeFreeText': 'volume_free_text',
            'Extent': 'extent',
            'ExtentNote': 'extent_note',
        },
        'authority': {
            'ClassificationSystem': 'classification_system',
            'ClassificationCode': 'classification_code',
            'ClassificationHierarchy': 'classification_hierarchy',
            'RedirectTo': 'redirect_to',
        },
        'person': {
            'PersonalNameFirst': 'personal_name_first',
            'PersonalNameLast': 'personal_name_last',
            'PersonalNameSuffix': 'personal_name_suffix',
            'PersonalNamePreferredForm': 'personal_name_preferred'
        },
        'acrelation': {
            'ID.Authority.link': 'authority',
            'ID.Citation.link': 'citation',
            'Type.Broad.controlled': 'type_broad_controlled',
            'PersonalNameFirst': 'personal_name_first',
            'PersonalNameLast': 'personal_name_last',
            'PersonalNameSuffix': 'personal_name_suffix',
        },
        'ccrelation': {
            'ID.Subject.link': 'subject',
            'ID.Object.link': 'object',
        },
        'tracking': {
            'ID.Subject.link': 'subject',
            'TrackingInfo': 'tracking_info',
            'Notes': 'notes',
        },
        'attribute': {
            'ID.Subject.link': 'subject',
            'DateAttribute.free': 'value_freeform',
            'DateBegin': ('value', 'type_qualifier'),
            'DateEnd': ('value', 'type_qualifier'),
            'Type.Broad.controlled': 'type_controlled_broad',
        },
        'linkeddata': {
            'AccessStatus': 'access_status',
            'AccessStatusDateVerified': 'access_status_date_verified',
            'ID.Subject.link': 'subject',
            'Type.Broad.controlled': 'type_controlled_broad',
            'UniversalResourceName.link': 'universal_resource_name',
            'NameOfResource': 'resource_name',
            'URLOfResource': 'url',
        }
    }

    mappings = {
        'classification_system': {
            'WELDON THESAURUS TERMS (2002-PRESENT)': 'SWP',
            'WELDON THESAURUS': 'SWP',
            'WELDON CLASSIFICATION SYSTEM (2002-PRESENT)': 'SWP',
            'SWP': 'SWP',
            'NEU': 'NEU',
            'MW': 'MW',
            'SHOT': 'SHOT',
            'SHOT THESAURUS TERMS': 'SHOT',
            'GUERLAC COMMITTEE CLASSIFICATION SYSTEM (1953-2001)': 'GUE',
            'WHITROW CLASSIFICATION SYSTEM (1913-1999)': 'MW',
            'FORUM FOR THE HISTORY OF SCIENCE IN AMERICA': 'FHSA',
            'SEARCH APP CONCEPT': 'SAC',
        },
        'type_broad_controlled': {
            'acrelation': {
                'HasPersonalResponsibilityFor': 'PR',
                'ProvidesSubjectContentAbout': 'SC',
                'IsInstitutionalHostOf': 'IH',
                'IsPublicationHostOf': 'PH',
            }
        },
        'created_on_fm': _as_datetime,
        'modified_on_fm': _as_datetime,
        'extent': _try_int,
        'issue_begin': _try_int,
        'issue_end': _try_int,
        'page_begin': _try_int,
        'page_end': _try_int,
        'volume_begin': _try_int,
        'volume_end': _try_int,
        'data_display_order': _to_float,
        'access_status_date_verified': _as_datetime,
        ('public', 'record_status_value', 'record_status_explanation'): _handle_record_status,
        ('value', 'type_qualifier'): {
            'attribute': _handle_attribute_value,
        },
        'type_controlled': {
            'citation': {
                'Book': 'BO',
                'Article': 'AR',
                'Chapter': 'CH',
                'Review': 'RE',
                'EssayReview': 'ES',
                'Thesis': 'TH',
                'Event': 'EV',
                'Presentation': 'PR',
                'InteractiveResource': 'IN',
                'Website': 'WE',
                'Application': 'AP',
            },
            'authority': {
                'Person': 'PE',
                'Institution': 'IN',
                'TimePeriod': 'TI',
                'GeographicTerm': 'GE',
                'SerialPublication': 'SE',
                'ClassificationTerm': 'CT',
                'Concept': 'CO',
                'CreativeWork': 'CW',
                'Event': 'EV',
                'Publishers': 'PU',
                'Cross-reference': 'CR',
            },
            'acrelation': {
                'Author': 'AU',
                'Editor': 'ED',
                'Advisor': 'AD',
                'Contributor': 'CO',
                'Translator': 'TR',
                'Subject': 'SU',
                'Category': 'CA',
                'Publisher': 'PU',
                'School': 'SC',
                'Institution': 'IN',
                'Meeting': 'ME',
                'Periodical': 'PE',
                'BookSeries': 'BS'
            },
            'ccrelation': {
                'includesChapter': 'IC',
                'includesSeriesArticle': 'ISA',
                'isReviewOf': 'RO',
                'isReviewedBy': 'RB',
                'respondsTo': 'RE',
                'isAssociatedWith': 'AS'
            },
            'tracking': {
                'HSTMUpload': 'HS',
                'Printed': 'PT',
                'Authorized': 'AU',
                'Proofed': 'PD',
                'FullyEntered': 'FU',
                'Bulk Data Update': 'BD'
            }
        }
    }

    def __init__(self, handler):
        self.handler = handler

    def _map_field_value(self, model_name, fm_field, fm_value):
        """
        Given a model and a filemaker field/value pair, obtain the correct
        model field and value.

        The configuration in FMPDSOParser.mappings is used to convert
        ``fm_value`` to the correct Python type for the identified model field.

        Parameters
        ----------
        model_name : str
            Must be the (lowercase normed) name of a model in
            :mod:`isiscb.isisdata.models`\.
        fm_field : str
            Name of a field in the FileMaker database.
        fm_value : str
            Raw value from the FileMaker database.

        Returns
        -------
        model_field : str
        value
            The type of this object will depend on the model field.
        """
        if not fm_value:
            return []

        model_field = self.fields.get(fm_field, None)
        if not model_field:
            model_field = self.fields[model_name].get(fm_field, None)
            if not model_field:
                return []    # Skip the field.


        mapper = self.mappings.get(model_field, None)
        value = copy.copy(fm_value)
        if mapper:
            # The mapping may apply to all models with this field.
            if hasattr(mapper, '__call__') or type(mapper) is staticmethod:
                value = self.mappings[model_field].__func__(model_name, fm_field, value)

            # And/or be model-specific.
            elif hasattr(mapper, 'get'):
                mapper = mapper.get(model_name, None)
                if mapper:
                    # The mapper itself may be a function, or...
                    if hasattr(mapper, '__call__') or type(mapper) is staticmethod:
                        value = mapper.__func__(model_name, fm_field, value)
                    # ...a hashmap (dict).
                    elif hasattr(mapper, 'get'):
                        value = mapper.get(value, value)



        # A single field/value in FM may map to two or more fields/values in
        #  IsisCB Explore.
        if type(model_field) is tuple and type(value) is tuple:
            return zip(model_field, value)
        return [(model_field, value)]

    def _get_handler(self, model_name):
        return getattr(self.handler, 'handle_%s' % model_name, None)

    def _tag(self, element):
        return copy.copy(element.tag).replace(self.fm_namespace, '')

    def parse_record(self, record, model_name, parse_also=None):
        if self._tag(record) != 'ROW':
            return

        fielddata = []
        extra = [[] for _ in parse_also]
        for element in record.getchildren():
            fm_field = self._tag(element)
            fm_value = copy.copy(element.text)
            fielddata += self._map_field_value(model_name, fm_field, fm_value)
            if parse_also:
                for i, extra_model in enumerate(parse_also):
                    extra[i] += self._map_field_value(extra_model, fm_field, fm_value)

        handler = self._get_handler(model_name)
        if not handler:
            return
        return handler(fielddata, extra)

    def parse(self, model_name, data_path, parse_also):
        fast_iter(ET.iterparse(data_path), self.parse_record, model_name, parse_also)


class VerboseHandler(object):
    def handle_citation(self, fielddata, extra):
        pprint.pprint(fielddata)

    def handle_authority(self, fielddata, extra):
        pprint.pprint(fielddata)




class Command(BaseCommand):
    help = 'Load FileMaker data from XML'

    def __init__(self, *args, **kwargs):
        self.failed = []
        return super(Command, self).__init__(*args, **kwargs)

    def _get_subject(self, subject_id):
        model_name = model_ids[subject_id[:3]]
        subject_ctype = ContentType.objects.get(model=model_name).id
        return subject_ctype

    def add_arguments(self, parser):
        parser.add_argument('datapath', nargs=1, type=str)
        parser.add_argument('table', nargs='*', type=str)

    def handle(self, *args, **options):
        handler = VerboseHandler()
        parser = FMPDSOParser(handler)
        table = options['table'][0]
        path = os.path.join(options['datapath'][0], '%s.xml' % table)
        parser.parse(table, path, [])
