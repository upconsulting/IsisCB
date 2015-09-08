from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist, FieldError, ValidationError
from django.contrib.contenttypes.models import ContentType
from isisdata.models import *

import datetime
import xml.etree.ElementTree as ET
import os
import copy

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
    try:
        return datetime.datetime.strptime(x, datetime_format)
    except ValueError:
        try:
            return datetime.datetime.strptime(x, datetime_format_2)
        except ValueError:
            try:
                return datetime.datetime.strptime(x, date_format)
            except ValueError:
                return datetime.datetime.strptime(x, date_format_2)


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
    'Content List': 'CL',
    'Source Book': 'SB',
    'Scope': 'SC',
    'Fix Record': 'FX',
    'Duplicate': 'DP'
}

recordActionTypes = {
    'ExternalProof': 'EX',
    'QueryProof': 'QU',
    'Hold': 'HO',
    'RLGCorrect': 'RC'
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
    'StatusOfRecord': ('status_of_record', lambda x: statusOfRecordTypes[x])
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
    'Cross-reference': ''
}

# Translates fields from FM Authority:RecordStatus to Authority.record_status
recordStatusTypes = {
    'ACTIVE': 'AC',
    'DUPLICATE': 'DU',
    'REDIRECT': 'RD',
    'DELETE': 'DL',
    'NEEDSTOBEFIXED': 'NF'
}

classificationSystems = {
    'WELDON THESAURUS TERMS (2002-PRESENT)': 'SWP',
    'SWP': 'SWP',
    'NEU': 'NEU',
    'MW': 'MW',
    'SHOT': 'SHOT',
    'SHOT THESAURUS TERMS': 'SHOT',
    'GUERLAC COMMITTEE CLASSIFICATION SYSTEM (1953-2001)': 'GUE',
    'WHITROW CLASSIFICATION SYSTEM (1913-1999)': 'MW',
    'WELDON CLASSIFICATION SYSTEM (2002-PRESENT)': 'SWP',
    'FORUM FOR THE HISTORY OF SCIENCE IN AMERICA': 'FHSA',
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
    'RecordStatus': ('record_status', lambda x: recordStatusTypes[x.upper()]),
    'RecordHistory': ('record_history', passthrough),
    'PersonalNameFirst': ('personal_name_first', passthrough),
    'PersonalNameLast': ('personal_name_last', passthrough),
    'PersonalNameSuffix': ('personal_name_suffix', passthrough),
    'RedirectTo': ('redirect_to', passthrough)
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
    'DataSourceField': ('administrator_notes', passthrough)
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
    'AdministratorNotes': ('administrator_notes', passthrough)
}

# Maps fields from FM Attributes to Attribute model.
# TODO: revise this based on changes to Attribute model, and discussion of
#  Attribute.value field.
attributeFields = {
    'ID': ('id', passthrough),
    'ID.Subject.link': ('subject', passthrough),
    'DateAttribute.free': ('value_freeform', try_int),    # TODO: this is temporary.
    'DateBegin': ('value', as_datetime),
    'CreatedBy': ('created_by_fm', passthrough),
    'CreatedOn': ('created_on_fm', as_datetime),
    'ModifiedBy': ('modified_by_fm', passthrough),
    'ModiefiedOn': ('modified_on_fm', as_datetime), # Typo in data.
    'Type.controlled': ('type_controlled', passthrough),
    'Type.Broad.controlled': ('type_controlled_broad', passthrough),
    'Type.free': ('type_free', passthrough),
    'RecordHistory': ('record_history', passthrough),
    'Notes': ('administrator_notes', passthrough)
}

# Maps FM Tracking.Type.controlled to Tracking.type_controlled field.
trackingTypes = {
    'HSTMUpload': 'HS',
    'Printed': 'PT',
    'Authorized': 'AU',
    'Proofed': 'PD',
    'FullyEntered': 'FU'
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
    'Notes': ('notes', passthrough)
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
    'UniversalResourceName.link': ('universal_resource_name', passthrough)
}


# TODO: This could be about 10 times DRYer....
# TODO: Add handle_aa_relations method (there are no AA Relations in the FM
#  database right now).
class Command(BaseCommand):
    help = 'Load FileMaker data from XML'

    namespaces = {'fm': fm_namespace}

    def __init__(self, *args, **kwargs):
        self.failed = []
        return super(Command, self).__init__(*args, **kwargs)

    def _get_subject(self, subject_id):
        subject_instance = None
        subject_ctype = None
        for ctype in ContentType.objects.all():
            if ctype.model.startswith('historical'):    # e.g. HistoricalRecord.
                continue

            model = ctype.model_class()
            try:
                subject_instance = model.objects.get(id=subject_id)
                subject_ctype = ctype
                break   # Found.
            except (ValueError, FieldError, ObjectDoesNotExist):
                pass
        return subject_instance, subject_ctype

    def add_arguments(self, parser):
        parser.add_argument('datapath', nargs=1, type=str)
        parser.add_argument('table', nargs='*', type=str)

    def handle(self, *args, **options):

        datapath = options['datapath'][0]
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

    def handle_citations(self, datapath):
        citationspath = os.path.join(datapath, 'citations.xml')

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

            if 'language' in values:
                language = copy.deepcopy(values['language'])
                del values['language']
                try:
                    language_instance = Language.objects.get(name=language)
                except ObjectDoesNotExist:
                    print "couldn't find language {0}".format(language)
                    language_instance = None
                    pass

            try:
                instance = Citation(**values)
                pd_instance = PartDetails(**partDetails)
                pd_instance.save()
                instance.part_details = pd_instance
                instance.save()
                if language_instance is not None:
                    instance.language.add(language_instance)
                instance.save()
            except Exception as E:
                self.failed.append((values['id'], E.message))
                raise E
            r.clear()

        context = ET.iterparse(citationspath)
        fast_iter(context, process_elem)

    def handle_authorities(self, datapath):
        authoritiespath = os.path.join(datapath, 'authorities.xml')
        missed_relations = []

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

            if 'redirect_to' in values:
                # The target of the redirect may not have been added yet. If
                #  that is so, fail quietly and save the redirect information
                #  for later.
                try:
                    values['redirect_to'] = Authority.objects.get(id=values['redirect_to'])
                except ObjectDoesNotExist:
                    missed_relations.append((values['id'], values['redirect_to']))
                    del values['redirect_to']

            if values['type_controlled'] == 'PE':
                model = Person
            else:
                model = Authority

            try:
                instance = model(**values)
                instance.save()
            except Exception as E:
                raise E
            r.clear()

        context = ET.iterparse(authoritiespath)
        fast_iter(context, process_elem)

        # Go back and attempt to add in redirects that were missed the first
        #  time around.
        for id_from, id_to in missed_relations:
            # It is possible that the target record does not exist. If so,
            #  there's not much we can do at this point.
            try:
                instance = Authority.objects.get(id=id_from)
                instance_to = Authority.objects.get(id=id_to)
                instance.redirect_to = instance_to
                instance.save()
            except ObjectDoesNotExist:
                pass

    def handle_ac_relations(self, datapath):
        acrelationspath = os.path.join(datapath, 'ac_relations.xml')

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

            try:
                authority = Authority.objects.get(id=values['authority'])
                values['authority'] = authority
                citation = Citation.objects.get(id=values['citation'])
                values['citation'] = citation
            except ObjectDoesNotExist as E:
                # TODO: this should fail quietly and move on?
                self.failed.append((values['id'], E.message))
                return

            instance = ACRelation(**values)
            instance.save()
            r.clear()

        context = ET.iterparse(acrelationspath)
        fast_iter(context, process_elem)

    def handle_cc_relations(self, datapath):
        ccrelationspath = os.path.join(datapath, 'cc_relations.xml')

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

            try:
                subject_instance = Citation.objects.get(id=values['subject'])
                values['subject'] = subject_instance
                object_instance = Citation.objects.get(id=values['object'])
                values['object'] = object_instance
            except ObjectDoesNotExist as E:
                # TODO: this should fail quietly and move on?
                self.failed.append((values['id'], E.message))
                return

            instance = CCRelation(**values)
            instance.save()
            r.clear()

        context = ET.iterparse(ccrelationspath)
        fast_iter(context, process_elem)

    def handle_attributes(self, datapath):
        attributesspath = os.path.join(datapath, 'attributes.xml')

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
                        value = method(value)
                        values[dj_field] = value

            if 'subject' not in values:
                self.failed.append((values['id'], 'missing subject'))
                return

            vtype = dict(VALUE_MODELS)[type(values['value'])]
            value_value = copy.deepcopy(values['value'])
            del values['value']     # Not accepted by Attribute constructor.

            vctype = ContentType.objects.get(model=vtype.__name__.lower())
            type_controlled = values['type_controlled']
            defaults = {'value_content_type': vctype}
            atype = AttributeType.objects.get_or_create(name=type_controlled,
                                                        defaults=defaults)[0]
            values['type_controlled'] = atype

            subject_id = copy.deepcopy(values['subject'])
            del values['subject']   # Not accepted by Attribute constructor.

            subject_instance, subject_ctype = self._get_subject(subject_id)

            if subject_instance is None:
                self.failed.append((values['id'], 'no such subject'))
                return

            values['source_content_type'] = subject_ctype
            values['source_instance_id'] = subject_instance.id

            instance = Attribute(**values)
            instance.save()
            # subject_instance.attributes.add(instance)
            # subject_instance.save()
            value = vtype(value=value_value, attribute=instance)
            value.save()

            r.clear()

        context = ET.iterparse(attributesspath)
        fast_iter(context, process_elem)

    def handle_tracking(self, datapath):
        trackingpath = os.path.join(datapath, 'tracking.xml')

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
            del values['subject']

            try:
                subject_instance, subject_ctype = self._get_subject(subject_id)
                values['subject'] = subject_instance
            except ObjectDoesNotExist as E:
                # TODO: this should fail quietly and move on?
                self.failed.append((values['id'], E.message))
                return

            values['subject_content_type'] = subject_ctype
            values['subject_instance_id'] = subject_instance.id

            instance = Tracking(**values)
            instance.save()
            r.clear()

        context = ET.iterparse(trackingpath)
        fast_iter(context, process_elem)

    def handle_linkeddata(self, datapath):
        linkeddatapath = os.path.join(datapath, 'linked_data.xml')

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
            values['type_controlled'] = ltype

            if 'subject' not in values:
                self.failed.append((values['id'], 'missing subject'))
                return

            subject_id = copy.deepcopy(values['subject'])
            del values['subject']

            try:
                subject_instance, subject_ctype = self._get_subject(subject_id)
                # values['subject'] = subject_instance
            except ObjectDoesNotExist as E:
                # TODO: this should fail quietly and move on?
                self.failed.append((values['id'], E.message))
                return

            values['subject_content_type'] = subject_ctype
            values['subject_instance_id'] = subject_instance.id

            instance = LinkedData(**values)
            instance.save()
            r.clear()


        context = ET.iterparse(linkeddatapath)
        fast_iter(context, process_elem)
