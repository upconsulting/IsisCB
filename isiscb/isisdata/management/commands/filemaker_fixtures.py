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

fm_namespace = '{http://www.filemaker.com/fmpdsoresult}'

datetime_format = '%m/%d/%Y %I:%M:%S %p'
datetime_format_2 = '%m/%d/%Y %I:%M %p'
date_format = '%m/%d/%Y'
date_format_2 = '%Y'

passthrough = lambda x: x
as_int = lambda x: int(x)
as_upper = lambda x: x.upper()

# TODO: Make this more DRY.
def as_datetime(x):
    formats = [datetime_format, datetime_format_2, date_format, date_format_2]
    val = None
    for format in formats:
        try:
            val = datetime.datetime.strptime(x, format)
        except ValueError:
            pass
    # if val is None:
    #     raise ValueError('Could not coerce value to datetime')
    return val


def try_int(v):
    try:
        return int(v)
    except ValueError:
        return v


# Translates values from FM Citation:Type.controlled to Citation.type_controlled
citationTypes = {
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
}

statusOfRecordTypes = {
    'Contents List': 'CL',
    'Source Book': 'SB',
    'Source Book (of Chap or Rev)': 'SB',
    'Scope': 'SC',
    'Fix Record': 'FX',
    'Fix record. No publication date.': 'FX',
    'Fix Record. See BibliographerNotes.': 'FX',
    'Broken': 'FX',
    'Duplicate': 'DP',
    'Delete': 'DL',
    'IsisRLG': 'RL',
}

recordActionTypes = {
    'ExternalProof': 'EX',
    'QueryProof': 'QU',
    'Query SPW': 'QU',
    'Hold': 'HO',
    'RLG Correct': 'RC'
}

# Translates field names in FM Citation to field names and conversion methods
#  for Citation model.
citationFields = {
    'ID': ('id', passthrough),
    'Title': ('title', passthrough),
    'Type.controlled': ('type_controlled', lambda x: citationTypes[x]),
    'Abstract': ('abstract', passthrough),
    'Description': ('description', passthrough),
    'EditionDetails': ('edition_details', passthrough),
    'PhysicalDetails': ('physical_details', passthrough),
    'NotesOnContent.notpublished': ('administrator_notes', passthrough),
    'NotesOnProvenance': ('record_history', passthrough),
    'CreatedBy': ('created_by_fm', passthrough),
    'CreatedOn': ('created_on_fm', as_datetime),
    'ModifiedBy': ('modified_by_fm', passthrough),
    'ModifiedOn': ('modified_on_fm', as_datetime),
    'Language': ('language', passthrough),
    'RecordAction': ('record_action', lambda x: recordActionTypes[x]),
    'StatusOfRecord': ('status_of_record', lambda x: statusOfRecordTypes[x]),
    'RecordStatus': ('public', lambda x: x.lower() == 'public'),
}

# Translates fields from FM Citation to PartDetails model.
partFields = {
    'Issue_Begin': ('issue_begin', as_int),
    'Issue_End': ('issue_end', as_int),
    'Issue_FreeText': ('issue_free_text', passthrough),
    'Page_Begin': ('page_begin', as_int),
    'Page_End': ('page_end', as_int),
    'Pages_FreeText': ('pages_free_text', passthrough),
    'Volume_End': ('volume_end', as_int),
    'Volume_Begin': ('volume_begin', as_int),
    'Volume_FreeText': ('volume_free_text', passthrough),
}

# Translates fields from FM Authority:Type.controlled to
#  Authority.type_controlled
authorityTypes = {
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
}

# Translates fields from FM Authority:RecordStatus to Authority.record_status
recordStatusTypes = {
    'Active': 'AC',
    'Duplicate': 'DU',
    'Redirect': 'RD',
    'DELETE': 'DL',
    'Delete': 'DL',
    'NeedsToBeFixed': 'NF',
    'Inactive': 'IN'
}

classificationSystems = {
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
}

# Translates fields from FM Authority to Authority model.
authorityFields = {
    'ID': ('id', passthrough),
    'Name': ('name', passthrough),
    'Type.controlled': ('type_controlled', lambda x: authorityTypes.get(x, None)),
    'ClassificationSystem': ('classification_system', lambda x: classificationSystems[x.upper()]),
    'ClassificationCode': ('classification_code', passthrough),
    'ClassificationHierarchy': ('classification_hierarchy', passthrough),
    'NotesOnContent': ('administrator_notes', passthrough),
    'NotesOnProvenance': ('record_history', passthrough),
    'Description': ('description', passthrough),
    'CreatedBy': ('created_by_fm', passthrough),
    'CreatedOn': ('created_on_fm', as_datetime),
    'ModifiedBy': ('modified_by_fm', passthrough),
    'ModifiedOn': ('modified_on_fm', as_datetime),
    'RecordStatus': ('record_status', lambda x: recordStatusTypes[x]),
    'RecordHistory': ('record_history', passthrough),
    'PersonalNameFirst': ('personal_name_first', passthrough),
    'PersonalNameLast': ('personal_name_last', passthrough),
    'PersonalNameSuffix': ('personal_name_suffix', passthrough),
    'RedirectTo': ('redirect_to', passthrough),
}

# Maps FM AC_Relationship:Type.controlled to ACRelation.type_controlled
acRelationTypes = {
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
}

ccRelationTypes = {
    'includesChapter': 'IC',
    'includesSeriesArticle': 'ISA',
    'isReviewOf': 'RO',
    'isReviewedBy': 'RB',
    'respondsTo': 'RE',
    'isAssociatedWith': 'AS'
}

# Maps FM AC_Relationship:Type.Broad.controlled to
#  ACRelation.type_broad_controlled
acRelationTypesBroad = {
    'HasPersonalResponsibilityFor': 'PR',
    'ProvidesSubjectContentAbout': 'SC',
    'IsInstitutionalHostOf': 'IH',
    'IsPublicationHostOf': 'PH',
}

# Maps fields from FM AC_Relationship to ACRelation model.
ACRelationFields = {
    'ID': ('id', passthrough),
    'Authority8DigitID': ('authority_alt', passthrough),
    'Citation8DigitID': ('citation_alt', passthrough),
    'ID.Authority.link': ('authority', passthrough),
    'ID.Citation.link': ('citation', passthrough),
    'description': ('description', passthrough),
    'CreatedBy': ('created_by_fm', passthrough),
    'CreatedOn': ('created_on_fm', as_datetime),
    'ModifiedBy': ('modified_by_fm', passthrough),
    'ModifiedOn': ('modified_on_fm', as_datetime),
    'Name': ('name', passthrough),
    'Type.controlled': ('type_controlled', lambda x: acRelationTypes[x]),
    'Type.Broad.controlled': ('type_broad_controlled',
                              lambda x: acRelationTypesBroad[x]),
    'Type.free': ('type_free', passthrough),
    'ConfidenceMeasure': ('confidence_measure', passthrough),
    'RelationshipWeight': ('relationship_weight', passthrough),
    'RecordHistory': ('record_history', passthrough),
    'NameForDisplayInCitation': ('name_for_display_in_citation', passthrough),
    'DataSourceField': ('administrator_notes', passthrough),
    'NameAsEntered': ('name_as_entered', passthrough),
    'DataDisplayOrder': ('data_display_order', lambda x: float(x)),
    'RecordStatus': ('public', lambda x: x.lower() == 'public'),
}

# Maps fields from FM CC_Relationship to CCRelation model.
CCRelationFields = {
    'ID': ('id', passthrough),
    'SubjectID8Digit': ('subject_alt', passthrough),
    'ObjectID8Digit': ('object_alt', passthrough),
    'ID.Subject.link': ('subject', passthrough),
    'ID.Object.link': ('object', passthrough),
    'description': ('description', passthrough),
    'CreatedBy': ('created_by_fm', passthrough),
    'CreatedOn': ('created_on_fm', as_datetime),
    'ModifiedBy': ('modified_by_fm', passthrough),
    'ModiefiedOn': ('modified_on_fm', as_datetime), # Typo in data.
    'name': ('name', passthrough),
    'Type.controlled': ('type_controlled', lambda x: ccRelationTypes[x]),
    'Type.free': ('type_free', passthrough),
    'ConfidenceMeasure': ('confidence_measure', passthrough),
    'RelationshipWeight': ('relationship_weight', passthrough),
    'RecordHistory': ('record_history', passthrough),
    'AdministratorNotes': ('administrator_notes', passthrough),
    'RecordStatus': ('public', lambda x: x.lower() == 'public'),
}

# Maps fields from FM Attributes to Attribute model.
# TODO: revise this based on changes to Attribute model, and discussion of
#  Attribute.value field.
attributeFields = {
    'ID': ('id', passthrough),
    'ID.Subject.link': ('subject', passthrough),
    'DateAttribute.free': ('value_freeform',
                           lambda x: try_int(x.replace('[', '').replace(']', ''))),
    'DateBegin': ('value', lambda x: as_datetime(x).date()),
    'CreatedBy': ('created_by_fm', passthrough),
    'CreatedOn': ('created_on_fm', as_datetime),
    'ModifiedBy': ('modified_by_fm', passthrough),
    'ModiefiedOn': ('modified_on_fm', as_datetime), # Typo in data.
    'Type.controlled': ('type_controlled', passthrough),
    'Type.Broad.controlled': ('type_controlled_broad', passthrough),
    'Type.free': ('type_free', passthrough),
    'RecordHistory': ('record_history', passthrough),
    'Notes': ('administrator_notes', passthrough),
    'RecordStatus': ('public', lambda x: x.lower() == 'public'),
}

# Maps FM Tracking.Type.controlled to Tracking.type_controlled field.
trackingTypes = {
    'HSTMUpload': 'HS',
    'Printed': 'PT',
    'Authorized': 'AU',
    'Proofed': 'PD',
    'FullyEntered': 'FU',
    'Bulk Data Update': 'BD'
}

# Maps fields from FM Tracking to Tracking model.
trackingFields = {
    'ID': ('id', passthrough),
    'ID.Subject.link': ('subject', passthrough),
    'CreatedBy': ('created_by_fm', passthrough),
    'CreatedOn': ('created_on_fm', as_datetime),
    'ModifiedBy': ('modified_by_fm', passthrough),
    'ModifiedOn': ('modified_on_fm', as_datetime),
    'Type.controlled': ('type_controlled', lambda x: trackingTypes[x]),
    'TrackingInfo': ('tracking_info', passthrough),
    'Notes': ('notes', passthrough),
    'RecordStatus': ('public', lambda x: x.lower() == 'public'),
}


# Maps fields from FM LinkedData to LinkedData model.
# TODO: revisit the type fields as the model changes.
linkedDataFields = {
    'ID': ('id', passthrough),
    'ID.Subject.link': ('subject', passthrough),
    'CreatedBy': ('created_by_fm', passthrough),
    'CreatedOn': ('created_on_fm', as_datetime),
    'ModifiedBy': ('modified_by_fm', passthrough),
    'ModiefiedOn': ('modified_on_fm', as_datetime), # Typo in data.
    'Type.controlled': ('type_controlled', passthrough),
    'Type.Broad.controlled': ('type_controlled_broad', passthrough),
    'Type.free': ('type_free', passthrough),
    'RecordHistory': ('record_history', passthrough),
    'Notes': ('administrator_notes', passthrough),
    'UniversalResourceName.link': ('universal_resource_name', passthrough),
    'RecordStatus': ('public', lambda x: x.lower() == 'public'),
}



# TODO: This could be about 10 times DRYer....
# TODO: Add handle_aa_relations method (there are no AA Relations in the FM
#  database right now).
class Command(BaseCommand):
    help = 'Load FileMaker data from XML'

    chunk_size = 10000  # Number of instances to include in each fixture file.

    namespaces = {'fm': fm_namespace}

    def __init__(self, *args, **kwargs):
        self.failed = []
        return super(Command, self).__init__(*args, **kwargs)

    def _get_subject(self, subject_id):
        model_ids = {
            'CBB': 'citation',
            'CBA': 'authority',
            'ACR': 'acrelation',
            'AAR': 'aarelation',
            'CCR': 'ccrelation',
        }
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
            if 'authority_alt' in values:
                if 'authority' not in values:
                    values['authority'] = copy.copy(values['authority_alt'])
                del values['authority_alt']

            if 'citation_alt' in values:
                if 'citation' not in values:
                    values['citation'] = copy.copy(values['citation_alt'])
                del values['citation_alt']

            # But ultimately if we are missing either an authority or citation
            #  id there is no way to create a valid ACRelation.
            if 'authority' not in values or 'citation' not in values:
                self.failed.append((values['id'], 'missing citation or relation'))
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
            try:
                ltype = LinkedDataType.objects.get(name=type_controlled)
            except ObjectDoesNotExist:
                self.failed.append((values['id'], 'No such LinkedDataType.'))
                return

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
