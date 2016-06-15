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


def fast_iter(context, func):
    for event, e in context:
        func(e)
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
            'Page_Begin': 'page_begin',
            'Page_End': 'page_end',
            'Pages_FreeText': 'pages_free_text',
            'Volume_End': 'volume_end',
            'Volume_Begin': 'volume_begin',
            'Volume_FreeText': 'volume_free_text',
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
            'ID.Subject.link': 'subject', self.passthrough,
            'ID.Object.link': 'object', self.passthrough,
        },
        'tracking': {
            'ID.Subject.link': ('subject', self.passthrough),

            'TrackingInfo': ('tracking_info', self.passthrough),
            'Notes': ('notes', self.passthrough),
            'RecordStatus': ('public', lambda x: x.lower() == 'public'),
        },
        'attribute': {
            'ID.Subject.link': 'subject',
            'DateAttribute.free': 'value_freeform',
                                   lambda x: try_int(x.replace('[', '').replace(']', ''))),
            'DateBegin': ('value', lambda x: as_datetime(x).date()),

            'Type.Broad.controlled': 'type_controlled_broad',
            'RecordHistory': ('record_history', self.passthrough),


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
        'extent': int,
        'issue_begin': int,
        'issue_end': int,
        'page_begin': int,
        'page_end': int,
        'volume_begin': int,
        'volume_end': int,
        'data_display_order', float,
        'access_status_date_verified': _as_datetime,
        ('public', 'record_status_value', 'record_status_explanation'): _handle_record_status,
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

    @staticmethod
    def _as_datetime(value):
        """
        Attempt to coerce a value to ``datetime``.
        """
        for format in FMPDSOParser.datetime_formats + FMPDSOParser.date_formats:
            try:
                return datetime.datetime.strptime(value, format)
            except ValueError:
                pass
        return value

    @staticmethod
    def _try_int(value):
        try:
            return int(value)
        except ValueError:
            return value

    @staticmethod
    def _handle_record_status(value):

        match = re.match('(In)?[aA]ctive(.+)', value)
        if match:
            public_raw, explanation_raw = m.groups()
            public = True if public_raw else False
            explanation = explanation_raw.strip()
            status = 'Active' if public else 'Inactive'
        else:
            match = re.match('Redirect(.+)', value)
            if match:
                explanation_raw = match.groups()[0].strip()
                public, status, explanation = False, 'Redirect', explanation_raw
            else:
                public, status, explanation = False, 'Inactive', u''
        return public, status, explanation

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

        model_field = self.fields.get(fm_field, None)
        if not model_field:
            model_field = self.fields[model_name].get(fm_field, None)
            if not model_field:
                raise RuntimeError('No mapping for FM field %s on model %s' % (fm_field, model_name))


        mapper = self.mappings.get(model_field, None)
        if mapper:
            # The mapping may apply to all models with this field.
            if hasattr(mapper, '__call__'):
                value = self.mappings[model_field](value)

            # And/or be model-specific.
            if hasattr(mapper, 'get'):
                mapper = mapper.get(model_name, None)
                if mapper:
                    # The mapper itself may be a function, or...
                    if hasattr(mapper, '__call__'):
                        value = mapper(value)
                    # ...a hashmap (dict).
                    elif hasattr(mapper, 'get'):
                        value = mapper.get(value, value)

        # A single field/value in FM may map to two or more fields/values in
        #  IsisCB Explore.
        if type(model_field) is tuple and type(value) is tuple:
            return zip(model_field, value)
        return [(model_field, value)]





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
        self.chunk = 0
        datapath = options['datapath'][0]
        self.datapath = datapath
        tables = options['table']

        if tables is not None and len(tables) > 0:
            for table in tables:
                methodname = 'handle_{0}'.format(table)
                if hasattr(self, methodname):
                    method = getattr(self, methodname)
                    print 'Running', methodname,
                    method(datapath)
                    print '...done.'
        else:
            print 'Loading citations...',
            self.handle_citations(datapath)
            print 'done'
            print 'Loading authorities...',
            self.handle_authorities(datapath)
            print 'done'
            print 'Loading AC relations...',
            self.handle_ac_relations(datapath)
            print 'done'
            print 'Loading CC relations...',
            self.handle_cc_relations(datapath)
            print 'done'
            print 'Loading attributes...',
            self.handle_attributes(datapath)
            print 'done'
            print 'Loading linkeddata...',
            self.handle_linkeddata(datapath)
            print 'done'
            print 'Loading tracking...',
            self.handle_tracking(datapath)
            print 'done'
            #
            print 'The following data could not be inserted:'
            print self.failed

    def write_fixtures(self, data, name):
        outpath = os.path.join(self.datapath,
                               '{0}_{1}.json'.format(name, self.chunk))
        with open(outpath, 'w') as f:
            json.dump(data, f, indent=4)
        self.chunk += 1

    def to_fixture(self, values, model):
        for k, v in values.iteritems():
            if type(v) is datetime.datetime:
                values[k] = str(v) + '+00:00'
            if type(v) is datetime.date:
                values[k] = str(v)

        id = copy.copy(values['id'])
        del values['id']
        instance = {
            'pk': id,
            'model': model,
            'fields': values
        }
        return instance

    def handle_citations(self, datapath):
        self.pdPK = 1    # Use for PartDetails ID.

        with open('isisdata/fixtures/language.json', 'r') as f:
            languages = json.load(f)
        languageLookup = {l['fields']['name']: l['pk'] for l in languages}

        citationspath = os.path.join(datapath, 'citations.xml')
        self.citations = []
        self.part_details_instances = []

        def process_elem(r):
            if r.tag.replace(fm_namespace, '') != 'ROW':
                return

            partDetails = {}
            values = {}
            for elem in r.getchildren():
                field = copy.deepcopy(elem.tag.replace(fm_namespace, ''))
                value = copy.deepcopy(elem.text)

                if field in citationFields:
                    dj_field, method = citationFields[field]
                    if value is not None and value != 'None':
                        try:
                            value = method(value)
                        except KeyError as E:
                            value = ''
                            if dj_field == 'status_of_record':
                                for k, v in statusOfRecordTypes.iteritems():
                                    if k.lower() in value.lower():
                                        value = v
                            pass    # TODO: need better handling of bad data.
                        values[dj_field] = value
                if field in partFields:
                    pd_field, method = partFields[field]
                    if value is not None and value != 'None':
                        try:
                            value = method(value)
                        except ValueError:
                            # TODO: In some records, integer-only fields contain
                            #  non-integer data.
                            if 'volume' in pd_field:
                                pd_field = 'volume_free_text'
                            if 'issue' in pd_field:
                                pd_field = 'issue_free_text'
                            if 'page' in pd_field:
                                pd_field = 'pages_free_text'
                        partDetails[pd_field] = value

            language_instances = []
            if 'language' in values:
                language_tokens = re.split('\W+', values['language'])
                for language in language_tokens:
                    try:    # Get PK for language. Some words may be noise.
                        language_instances.append(languageLookup[language])
                    except KeyError:    # Unknown language.
                        pass
                del values['language']

            partDetails['id'] = copy.deepcopy(self.pdPK)  # PartDetails don't have an FM id.
            pd_instance = self.to_fixture(partDetails, 'isisdata.partdetails')
            self.part_details_instances.append(pd_instance)

            values['part_details'] = copy.deepcopy(self.pdPK)
            values['language'] = language_instances
            cit_instance = self.to_fixture(values, 'isisdata.citation')
            self.citations.append(cit_instance)

            self.pdPK += 1
            r.clear()
            print '\r', len(self.citations),

            if len(self.citations) == self.chunk_size:
                self.write_fixtures(self.citations, 'citations')
                self.citations = []
            if len(self.part_details_instances) == self.chunk_size:
                self.write_fixtures(self.part_details_instances, 'part_details')
                self.part_details_instances = []

        fast_iter(ET.iterparse(citationspath), process_elem)
        self.write_fixtures(self.citations, 'citations')
        self.write_fixtures(self.part_details_instances, 'part_details')


    def handle_authorities(self, datapath):
        authoritiespath = os.path.join(datapath, 'authorities.xml')
        self.redirect_authorities = []
        self.authorities = []
        self.persons = []

        def process_elem(r):
            if r.tag.replace(fm_namespace, '') != 'ROW':
                return

            values = {}
            for elem in r.getchildren():
                field = copy.deepcopy(elem.tag.replace(fm_namespace, ''))
                value = copy.deepcopy(elem.text)
                if field in authorityFields:
                    dj_field, method = authorityFields[field]
                    if value is not None and value != 'None':
                        value = method(value)
                        values[dj_field] = value

            model = 'isisdata.authority'
            if 'type_controlled' in values:
                if values['type_controlled'] == 'PE':
                    person_data = {'id': values['id']}
                    for k in ['personal_name_last',
                              'personal_name_first',
                              'personal_name_suffix']:
                        if k in values:
                            person_data[k] = copy.deepcopy(values[k])
                            del values[k]
                    person_instance = self.to_fixture(person_data,
                                                      'isisdata.person')
                    self.persons.append(person_instance)

            instance = self.to_fixture(values, model)
            if 'redirect_to' in values:
                self.redirect_authorities.append(instance)
            else:
                self.authorities.append(instance)

            # Set public field based on RecordStatus.
            if 'record_status' in values:
                values['public'] = values['record_status'] == 'AC'

            r.clear()
            print '\r', len(self.authorities),

            if len(self.authorities) == self.chunk_size:
                self.write_fixtures(self.authorities, 'authorities')
                self.authorities = []
            if len(self.persons) == self.chunk_size:
                self.write_fixtures(self.persons, 'persons')
                self.persons = []

        context = ET.iterparse(authoritiespath)
        fast_iter(context, process_elem)

        self.write_fixtures(self.authorities, 'authorities')
        self.write_fixtures(self.persons, 'persons')
        self.write_fixtures(self.redirect_authorities, 'authorities')


    def handle_ac_relations(self, datapath):
        acrelationspath = os.path.join(datapath, 'ac_relations.xml')

        self.acrelations = []

        def process_elem(r):
            if r.tag.replace(fm_namespace, '') != 'ROW':
                return

            values = {}
            for elem in r.getchildren():
                field = copy.deepcopy(elem.tag.replace(fm_namespace, ''))
                value = copy.deepcopy(elem.text)
                if field in ACRelationFields:
                    dj_field, method = ACRelationFields[field]

                    if value is not None and value != 'None':
                        value = method(value)
                        values[dj_field] = value

            # It is possible that we are missing authority or citation id.
            #  This is an attempt to salvage the record...
            if 'authority_alt' in values and 'authority' not in values:
                    values['authority'] = copy.copy(values['authority_alt'])
                del values['authority_alt']

            if 'citation_alt' in values and 'citation' not in values:
                    values['citation'] = copy.copy(values['citation_alt'])
                del values['citation_alt']

            # Only the citation is required; per ISISCB-378, we should support
            #  "headless" ACRelations with no linked Authority record.
            if 'citation' not in values:
                self.failed.append((values['id'], 'missing citation'))
                return

            relation = self.to_fixture(values, 'isisdata.acrelation')
            self.acrelations.append(relation)

            r.clear()
            print '\r', len(self.acrelations),

            if len(self.acrelations) == self.chunk_size:
                self.write_fixtures(self.acrelations, 'acrelations')
                self.acrelations = []

        context = ET.iterparse(acrelationspath)
        fast_iter(context, process_elem)
        self.write_fixtures(self.acrelations, 'acrelations')

    def handle_cc_relations(self, datapath):
        ccrelationspath = os.path.join(datapath, 'cc_relations.xml')
        self.ccrelations = []

        def process_elem(r):
            if r.tag.replace(fm_namespace, '') != 'ROW':
                return

            values = {}
            for elem in r.getchildren():
                field = copy.deepcopy(elem.tag.replace(fm_namespace, ''))
                value = copy.deepcopy(elem.text)

                if field in CCRelationFields:
                    dj_field, method = CCRelationFields[field]
                    if value is not None and value != 'None':
                        value = method(value)
                        values[dj_field] = value

            # It is possible that we are missing authority or citation id.
            #  This is an attempt to salvage the record...
            if 'subject_alt' in values:
                if 'subject' not in values:
                    values['subject'] = copy.copy(values['subject_alt'])
                del values['subject_alt']

            if 'object_alt' in values:
                if 'object' not in values:
                    values['object'] = copy.copy(values['object_alt'])
                del values['object_alt']

            # But ultimately if we are missing either an authority or citation
            #  id there is no way to create a valid ACRelation.
            if 'subject' not in values or 'object' not in values:
                self.failed.append((values['id'], 'missing subject or object'))
                return
            if 'CBB0' in [values['subject'], values['object']]:
                self.failed.append((values['id'], 'bad subject or object id'))
                return

            ccrelation = self.to_fixture(values, 'isisdata.ccrelation')
            self.ccrelations.append(ccrelation)

            r.clear()
            print '\r', len(self.ccrelations),

            if len(self.ccrelations) == self.chunk_size:
                self.write_fixtures(self.ccrelations, 'ccrelations')
                self.ccrelations = []

        context = ET.iterparse(ccrelationspath)
        fast_iter(context, process_elem)
        self.write_fixtures(self.ccrelations, 'ccrelations')

    def handle_attributes(self, datapath):
        attributesspath = os.path.join(datapath, 'attributes.xml')
        self.attributes = []
        self.values = []
        self.cvalues = []
        self.valuePK = 1
        self.attributeTypes = {}

        def process_elem(r):
            if r.tag.replace(fm_namespace, '') != 'ROW':
                return

            values = {}
            for elem in r.getchildren():
                field = copy.deepcopy(elem.tag.replace(fm_namespace, ''))
                value = copy.deepcopy(elem.text)
                if field in attributeFields:
                    dj_field, method = attributeFields[field]
                    if value is not None and value != 'None':
                        try:
                            value = method(value)
                        except (AttributeError, ValueError) as E:
                            self.failed.append((r, E.message))
                            return
                        values[dj_field] = value

            if 'subject' not in values:
                self.failed.append((values['id'], 'missing subject'))
                return

            if 'value' not in values:
                self.failed.append((values['id'], 'missing value'))
                return

            vtype = dict(VALUE_MODELS)[type(values['value'])]
            value_model = 'isisdata.{0}'.format(vtype.__name__.lower())
            value = copy.deepcopy(values['value'])

            value_values = {
                'id': copy.copy(self.valuePK),
                'attribute': values['id']
            }
            cvalue_values = {
                'id': copy.copy(self.valuePK),
                'value': value,
            }

            # 'value' is not accepted by the Attribute constructor.
            del values['value']

            if 'type_controlled' not in values:
                self.failed.append((values['id'], 'missing type'))
                return

            # Build fixture for Value parent instance.
            value_values['child_class'] = vtype.__name__
            value_fixture = self.to_fixture(value_values, 'isisdata.value')
            self.values.append(value_fixture)

            # Build fixture for Value child instance.
            cvalue_fixture = self.to_fixture(cvalue_values, value_model)
            self.cvalues.append(cvalue_fixture)

            self.valuePK += 1

            vctype = ContentType.objects.get(model=vtype.__name__.lower())

            type_controlled = values['type_controlled']
            if type_controlled not in self.attributeTypes:
                self.attributeTypes[type_controlled] = self.to_fixture({
                    'id': len(self.attributeTypes) + 1,
                    'name': type_controlled,
                    'value_content_type': vctype.id
                }, 'isisdata.attributetype')
            atype = self.attributeTypes[type_controlled]['pk']
            values['type_controlled'] = atype

            subject_id = copy.deepcopy(values['subject'])
            values['source_instance_id'] = subject_id
            values['source_content_type'] = self._get_subject(subject_id)
            del values['subject']   # Not accepted by Attribute constructor.

            instance = self.to_fixture(values, 'isisdata.attribute')
            self.attributes.append(instance)

            r.clear()
            print '\r', len(self.attributes),

            if len(self.attributes) == self.chunk_size:
                self.write_fixtures(self.attributes, 'attributes')
                self.attributes = []

            if len(self.values) == self.chunk_size:
                self.write_fixtures(self.values, 'values')
                self.values = []

            if len(self.cvalues) == self.chunk_size:
                self.write_fixtures(self.cvalues, 'cvalues')
                self.cvalues = []

        context = ET.iterparse(attributesspath)
        fast_iter(context, process_elem)
        self.write_fixtures(self.attributes, 'attributes')
        self.write_fixtures(self.attributeTypes.values(), 'attributetypes')
        self.write_fixtures(self.values, 'values')
        self.write_fixtures(self.cvalues, 'cvalues')
        print self.failed

    def handle_tracking(self, datapath):
        trackingpath = os.path.join(datapath, 'tracking.xml')
        self.trackings = []

        def process_elem(r):
            if r.tag.replace(fm_namespace, '') != 'ROW':
                return

            values = {}
            for elem in r.getchildren():
                field = copy.deepcopy(elem.tag.replace(fm_namespace, ''))
                value = copy.deepcopy(elem.text)
                if field in trackingFields:
                    dj_field, method = trackingFields[field]
                    if value is not None and value != 'None':
                        value = method(value)
                        values[dj_field] = value

            if 'subject' not in values:
                self.failed.append((values['id'], 'missing subject'))
                return

            subject_id = copy.deepcopy(values['subject'])
            subject_ctype = self._get_subject(subject_id)
            del values['subject']

            values['subject_content_type'] = subject_ctype
            values['subject_instance_id'] = subject_id

            instance = self.to_fixture(values, 'isisdata.tracking')
            self.trackings.append(instance)

            r.clear()
            print '\r', len(self.trackings),

            if len(self.trackings) == self.chunk_size:
                self.write_fixtures(self.trackings, 'trackings')
                self.trackings = []

        context = ET.iterparse(trackingpath)
        fast_iter(context, process_elem)
        self.write_fixtures(self.trackings, 'trackings')

    def handle_linkeddata(self, datapath):
        linkeddatapath = os.path.join(datapath, 'linked_data.xml')
        self.linkeddata = []

        def process_elem(r):
            if r.tag.replace(fm_namespace, '') != 'ROW':
                return

            values = {}
            for elem in r.getchildren():
                field = copy.deepcopy(elem.tag.replace(fm_namespace, ''))
                value = copy.deepcopy(elem.text)
                if field in linkedDataFields:
                    dj_field, method = linkedDataFields[field]
                    if value is not None and value != 'None':
                        value = method(value)
                        values[dj_field] = value

            if 'type_controlled' not in values:
                self.failed.append((values['id'], 'missing type'))
                return

            type_controlled = copy.deepcopy(values['type_controlled'])
            del values['type_controlled']

            ltype = LinkedDataType.objects.get_or_create(name=type_controlled)[0]
            print ltype

            try:
                ltype.is_valid(values['universal_resource_name'])
            except ValidationError:
                self.failed.append((values['id'], 'Invalid value.'))
                return
            values['type_controlled'] = ltype.id

            if 'subject' not in values:
                self.failed.append((values['id'], 'missing subject'))
                return

            subject_id = copy.deepcopy(values['subject'])
            del values['subject']

            subject_ctype = self._get_subject(subject_id)

            values['subject_content_type'] = subject_ctype
            values['subject_instance_id'] = subject_id

            instance = self.to_fixture(values, 'isisdata.linkeddata')
            self.linkeddata.append(instance)

            r.clear()
            print '\r', len(self.linkeddata),

            if len(self.linkeddata) == self.chunk_size:
                self.write_fixtures(self.linkeddata, 'linkeddata')
                self.linkeddata = []

        context = ET.iterparse(linkeddatapath)
        fast_iter(context, process_elem)
        self.write_fixtures(self.linkeddata, 'linkeddata')
