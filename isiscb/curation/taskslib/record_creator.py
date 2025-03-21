from __future__ import unicode_literals
from isisdata.models import *
import curation.curation_util as c_util
import curation.permissions_util as p_util

from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import transaction

from datetime import datetime
from dateutil.tz import tzlocal

import logging
import re

logger = logging.getLogger(__name__)

STATUS_MAP = {
    'Active': CuratedMixin.ACTIVE,
    'Delete': CuratedMixin.DUPLICATE,
    'Redirect': CuratedMixin.REDIRECT,
    'Inactive': CuratedMixin.INACTIVE
}

SUCCESS = 'SUCCESS'
ERROR = 'ERROR'
WARNING = 'WARNING'

RECORD_HISTORY = 'record_history'

LINKED_DATA_PREFIX = 'LinkedData::'
    
def _create_linkeddata(row, user_id, results, task_id, created_on):
    COL_LD_URN = 'LED URN'
    COL_LD_STATUS = 'LED Status'
    COL_LD_NOTE = 'LED Note'
    COL_LD_EXPLANATION = 'LED RecordStatusExplanation'
    COL_LD_RESOURCE = 'LED Resource'
    COL_LD_AUTHORITY = 'LED Subj ID'
    COL_LD_TYPE = 'LED Type'
    COL_AUTH_NAME = 'CBA Name'

    properties = {}

    if not row[COL_LD_AUTHORITY]:
        results.append((ERROR, "Authority missing", "", "There was no authority provided."))
        return
    else:
        subject_id = row[COL_LD_AUTHORITY]
        try:
            if subject_id.startswith(Authority.ID_PREFIX):
                subject = Authority.objects.get(pk=subject_id)
            else:
                subject = Citation.objects.get(pk=subject_id)

            properties.update({
                'subject': subject
            })
        except Exception as e:
            logger.error('Related record with id %s does not exist. Skipping attribute.' % (subject_id))
            logger.exception(e)
            results.append((ERROR, subject_id, subject_id, 'Related record does not exist.'))
            return

    _add_optional_simple_property(row, COL_LD_URN, properties, 'universal_resource_name')
    _add_optional_simple_property(row, COL_LD_NOTE, properties, 'administrator_notes')
    _add_status(row, COL_LD_STATUS, properties, results)
    _add_optional_simple_property(row, COL_LD_EXPLANATION, properties, 'record_status_explanation')
    _add_optional_simple_property(row, COL_LD_RESOURCE, properties, 'resource_name')

    if row[COL_LD_TYPE]:
        ld_type = row[COL_LD_TYPE]
        type_obj = LinkedDataType.objects.filter(name=ld_type).first()
        if type_obj:
            properties.update({
                'type_controlled_id': type_obj.pk
            })
        else:
            results.append((ERROR, subject_id, subject_id, "Object type does not exist: " + ld_type))
            logger.error('Linked Data Type %s does not exist. Skipping linked data.' % (ld_type))
            return

    if row[COL_AUTH_NAME] and type(subject) is Authority:
        auth_name = row[COL_AUTH_NAME]
        # check authority name
        if auth_name != subject.name:
            results.append((WARNING, subject_id, subject_id, "Related record name (%s) and provided name (%s) do not match."%(subject.name, auth_name)))

    _add_creation_note(properties, task_id, user_id, created_on)

    linked_data = LinkedData(**properties)
    _create_record(linked_data, user_id, results)

def _create_acrelation(row, user_id, results, task_id, created_on):
    COL_ACR_TYPE = 'ACR Type'
    COL_ACR_NAME_DISPLAY = 'ACR NameDisplay'
    COL_ACR_AUTHORITY_ID = 'ACR ID Auth'
    COL_ACR_CITATION_ID = 'ACR ID Cit'
    COL_ACR_DISPLAY_ORDER = 'ACR DataDisplayOrder'
    COL_ACR_CONFIDENCE = 'ACR ConfidenceMeasure'
    COL_ACR_NOTES = 'ACR Notes'
    COL_ACR_STATUS = 'ACR Status'
    COL_ACR_EXPLANATION = 'ACR RecordStatusExplanation'

    properties = {}

    if not _add_type(row, COL_ACR_TYPE, ACRelation, results, properties):
        return

    authority_id = row[COL_ACR_AUTHORITY_ID] if COL_ACR_AUTHORITY_ID in row else None
    if not authority_id:
        results.append((ERROR, "Authority missing", "", "There was no authority provided. Skipping."))
        return
   
    try:
        authority = _get_authority(authority_id, results, user_id)
        if not authority:
            return
    except Exception as e:
        logger.error(e)
        results.append((ERROR, "Authority does not exist", "", "There exists not authority with id %s. Skipping."%(authority_id)))
        return

    properties.update({
        'authority_id': authority.id
    })

    citation_id = row[COL_ACR_CITATION_ID]
    if not citation_id:
        results.append((ERROR, "Citation missing", "", "There was no citation provided. Skipping."))
        return

    try:
        Citation.objects.get(pk=citation_id)
    except Exception as e:
        logger.error(e)
        results.append((ERROR, "Citation does not exist", "", "There exists not citation with id %s. Skipping."%(citation_id)))
        return

    properties.update({
        'citation_id': citation_id,
    })

    _add_optional_simple_property(row, COL_ACR_NAME_DISPLAY, properties, 'name_for_display_in_citation')
    _add_optional_simple_property(row, COL_ACR_DISPLAY_ORDER, properties, 'data_display_order')
    _add_optional_simple_property(row, COL_ACR_CONFIDENCE, properties, 'confidence_measure')

    _add_optional_simple_property(row, COL_ACR_NOTES, properties, 'administrator_notes')
    _add_status(row, COL_ACR_STATUS, properties, results)
    _add_optional_simple_property(row, COL_ACR_EXPLANATION, properties, 'record_status_explanation')


    _add_creation_note(properties, task_id, user_id, created_on)

    acr_relation = ACRelation(**properties)
    _create_record(acr_relation, user_id, results)

def _get_authority(authority_id, results, user_id):
    if not authority_id.startswith(LINKED_DATA_PREFIX):
        try:
            return Authority.objects.get(pk=authority_id)
        except Exception as e:
            logger.error(e)
            results.append((ERROR, e, "", "There was an issue with authority id %s. Skipping."%(authority_id)))
            return None
        
    prefix_and_id = authority_id[len(LINKED_DATA_PREFIX):]
    prefix, id = prefix_and_id.split("::")
    user = User.objects.get(pk=user_id)   
    tenant = c_util.get_tenant(user)
    try:
        # there should be only one with the given id and of given type
        linked_data_entry = LinkedData.objects.filter(universal_resource_name=id, type_controlled__name=prefix)
        if linked_data_entry.count() > 1:
            logger.error("There are more than one linked data entry for %s and %s."%(prefix, id))
            results.append((ERROR, "More than one linked data entry.", "", "There are more than one linked data entry for %s. Skipping."%(prefix_and_id)))
            return None
        
        # TODO: check dataset for right permissions
        belongs_to = linked_data_entry.first().subject.belongs_to
        user = User.objects.get(pk=user_id)  

        if not belongs_to in p_util.get_accessible_dataset_objects(user):
            raise PermissionDenied("User cannot use authority %s from dataset %s."%(linked_data_entry.subject, belongs_to.name))
        
        return linked_data_entry.first().subject
    except Exception as e:
        logger.error(e)
        results.append((ERROR, "Linked data entry does not exist", "", "There exists no authority with linked data %s and %s. Skipping."%(prefix, id)))
        return None
        

def _create_aarelation(row, user_id, results, task_id, created_on):
    COL_AAR_TYPE = 'AAR Type'
    COL_AAR_OBJECT = 'AAR ID Obj'
    COL_AAR_SUBJECT = 'AAR ID Subj'
    COL_AAR_NOTES = 'AAR Notes'
    COL_AAR_STATUS = 'AAR Status'
    COL_AAR_EXPLANATION = 'AAR RecordStatusExplanation'

    properties = {}

    aartype_id = row[COL_AAR_TYPE]
    if not aartype_id:
        return

    try:
        aartype = AARelationType.objects.get(pk=aartype_id)
        properties.update({
            'aar_type': aartype
        })
    except Exception as e:
        logger.error(e)
        results.append((ERROR, "AARelationType does not exist", "", "There exists no aar type with id %s. Skipping."%(aartype_id)))
        return

    subject_id = row[COL_AAR_SUBJECT]
    try:
        authority = _get_authority(subject_id, results, user_id)
        if not authority:
            return
        # if subject was referenced via linked data, we need the authority id
        subject_id = authority.id
    except Exception as e:
        logger.error(e)
        results.append((ERROR, "Authority does not exist", "", "There exists no authority with id %s. Skipping."%(subject_id)))
        return

    properties.update({
        'subject_id': subject_id
    })

    object_id = row[COL_AAR_OBJECT]
    try:
        authority = _get_authority(object_id, results, user_id)
        if not authority:
            return
        # if subject was referenced via linked data, we need the authority id
        object_id = authority.id
    except Exception as e:
        logger.error(e)
        results.append((ERROR, "Authority does not exist", "", "There exists no authority with id %s. Skipping."%(object_id)))
        return

    properties.update({
        'object_id': object_id
    })

    _add_optional_simple_property(row, COL_AAR_NOTES, properties, 'administrator_notes')
    _add_status(row, COL_AAR_STATUS, properties, results)
    _add_optional_simple_property(row, COL_AAR_EXPLANATION, properties, 'record_status_explanation')

    _add_creation_note(properties, task_id, user_id, created_on)

    aar_relation = AARelation(**properties)
    _create_record(aar_relation, user_id, results)

def _create_ccrelation(row, user_id, results, task_id, created_on):
    COL_CCR_TYPE = 'CCR Type'
    COL_CCR_OBJECT = 'CCR ID Cit Obj'
    COL_CCR_SUBJECT = 'CCR ID Cit Subj'
    COL_CCR_DISPLAY_ORDER = 'CCR DataDisplayOrder'
    COL_CCR_NOTES = 'CCR Notes'
    COL_CCR_STATUS = 'CCR Status'
    COL_CCR_EXPLANATION = 'CCR RecordStatusExplanation'

    properties = {}

    if not _add_type(row, COL_CCR_TYPE, CCRelation, results, properties):
        return

    subject_id = row[COL_CCR_SUBJECT]
    try:
        Citation.objects.get(pk=subject_id)
    except Exception as e:
        logger.error(e)
        results.append((ERROR, "Citation does not exist", "", "There exists no citation with id %s. Skipping."%(subject_id)))
        return

    properties.update({
        'subject_id': subject_id
    })

    object_id = row[COL_CCR_OBJECT]
    try:
        Citation.objects.get(pk=object_id)
    except Exception as e:
        logger.error(e)
        results.append((ERROR, "Citation does not exist", "", "There exists not citation with id %s. Skipping."%(object_id)))
        return

    properties.update({
        'object_id': object_id
    })

    if row[COL_CCR_DISPLAY_ORDER]:
        properties.update({
            'data_display_order': row[COL_CCR_DISPLAY_ORDER]
        })

    _add_optional_simple_property(row, COL_CCR_NOTES, properties, 'administrator_notes')
    _add_status(row, COL_CCR_STATUS, properties, results)
    _add_optional_simple_property(row, COL_CCR_EXPLANATION, properties, 'record_status_explanation')

    _add_creation_note(properties, task_id, user_id, created_on)

    ccr_relation = CCRelation(**properties)
    _create_record(ccr_relation, user_id, results)

def _create_citation(row, user_id, results, task_id, created_on):
    COL_TYPE = 'CBB Type'
    COL_TITLE = 'CBB Title'
    COL_ABSTRACT = 'CBB Abstract'
    COL_DESCRIPTION = 'CBB Description'
    COL_ED_DETAILS = 'CBB EditionDetails'
    COL_LANGUAGE = 'CBB Language'
    COL_PHYS_DETAILS = 'CBB PhysicalDetails'
    COL_ISSUE_BEGIN = 'CBB IssueBegin'
    COL_ISSUE_END = 'CBB IssueEnd'
    COL_ISSUE_FREETEXT = 'CBB IssueFreeText'
    COL_PAGE_BEGIN = 'CBB PageBegin'
    COL_PAGE_END = 'CBB PageEnd'
    COL_PAGES_FREETEXT = 'CBB PagesFreeText'
    COL_VOL_BEGIN = 'CBB VolumeBegin'
    COL_VOL_END = 'CBB VolumeEnd'
    COL_VOL_FREETEXT = 'CBB VolumeFreeText'
    COL_EXTENT = 'CBB Extent'
    COL_EXTENT_NOTE = 'CBB ExtentNote'
    COL_DATASET = 'CBB Dataset'
    COL_NOTES = 'CBB Notes'
    COL_STATUS = 'CBB Status'
    COL_EXPLANATION = 'CBB RecordStatusExplanation'
    COL_COMPLETE_CITATION = 'CBB CompleteCitation'
    COL_STUB_RECORD_STATUS = 'CBB StubRecordStatus'
    COL_LINKED_DATA = 'CBB LinkedData'

    properties = {}

    if not _add_type(row, COL_TYPE, Citation, results, properties):
        return

    _add_optional_simple_property(row, COL_TITLE, properties, 'title')
    _add_optional_simple_property(row, COL_ABSTRACT, properties, 'abstract')
    _add_optional_simple_property(row, COL_DESCRIPTION, properties, 'description')
    _add_optional_simple_property(row, COL_ED_DETAILS, properties, 'edition_details')
    _add_optional_simple_property(row, COL_PHYS_DETAILS, properties, 'physical_details')
    _add_optional_simple_property(row, COL_COMPLETE_CITATION, properties, 'complete_citation')
    _add_optional_simple_property(row, COL_STUB_RECORD_STATUS, properties, 'stub_record_status')

    try:
        _add_dataset(row, COL_DATASET, user_id, properties, results)
    except PermissionDenied as e:
        results.append((ERROR, repr(e), "", ""))
        return
    except ObjectDoesNotExist as e:
        results.append((ERROR, "Dataset does not exist.", "", "The dataset %s does not exist."%(row[COL_DATASET])))
        return

    # create properties for part details
    properties_part_details = {}
    _add_optional_simple_property(row, COL_ISSUE_BEGIN, properties_part_details, 'issue_begin')
    _add_optional_simple_property(row, COL_ISSUE_END, properties_part_details, 'issue_end')
    _add_optional_simple_property(row, COL_ISSUE_FREETEXT, properties_part_details, 'issue_free_text')
    _add_optional_simple_property(row, COL_PAGE_BEGIN, properties_part_details, 'page_begin')
    _add_optional_simple_property(row, COL_PAGE_END, properties_part_details, 'page_end')
    _add_optional_simple_property(row, COL_PAGES_FREETEXT, properties_part_details, 'pages_free_text')
    _add_optional_simple_property(row, COL_VOL_BEGIN, properties_part_details, 'volume_begin')
    _add_optional_simple_property(row, COL_VOL_END, properties_part_details, 'volume_end')
    _add_optional_simple_property(row, COL_VOL_FREETEXT, properties_part_details, 'volume_free_text')
    _add_optional_simple_property(row, COL_EXTENT, properties_part_details, 'extent')
    _add_optional_simple_property(row, COL_EXTENT_NOTE, properties_part_details, 'extent_note')

    part_details = None
    citation_type = row[COL_TYPE]
    if citation_type in [Citation.ARTICLE, Citation.BOOK, Citation.REVIEW, Citation.CHAPTER, Citation.THESIS]:
        part_details = PartDetails(**properties_part_details)
    else:
        if properties_part_details:
            part_details = PartDetails(**properties_part_details)
            results.append((WARNING, "Part details info provided but record type (%s) does not use part details."%(citation_type), "", "Values were added but won't be visible."))

    if part_details:
        part_details.save()
        properties.update({
            'part_details_id': part_details.id
        })

    _add_optional_simple_property(row, COL_NOTES, properties, 'administrator_notes')
    _add_status(row, COL_STATUS, properties, results)
    _add_optional_simple_property(row, COL_EXPLANATION, properties, 'record_status_explanation')

    _add_creation_note(properties, task_id, user_id, created_on)

    
    with transaction.atomic():
        citation = Citation(**properties)
        _add_tenant(citation, user_id)
        
        linked_data_records, linked_data_identifiers = _add_linked_data(row, COL_LINKED_DATA, citation, results)

        language = row[COL_LANGUAGE] if COL_LANGUAGE in row else None
        language_obj = None
        if language:
            try:
                language_obj = Language.objects.filter(name=language).first()
            except Exception as e:
                logger.error(e)
                results.append((ERROR, "Language does not exist", "", "There exists no language %s."%(language)))

        _create_record(citation, user_id, results, alternate_ids=linked_data_identifiers)
        
        _save_linked_data_citation(linked_data_records, citation)
        if language_obj:
            citation.language.add(language_obj)
            citation.save()

def _create_authority(row, user_id, results, task_id, created_on):
    COL_TYPE = 'CBA Type'
    COL_NAME = 'CBA Name'
    COL_FIRST = 'CBA First'
    COL_LAST = 'CBA Last'
    COL_SUFFIX = 'CBA Suff'
    COL_PREFERRED = 'CBA Preferred'
    COL_REDIRECT = 'CBA Redirect'
    COL_CLASS_CODE = 'CBA ClassCode'
    COL_CLASS_HIERARCHY = 'CBA ClassHier'
    COL_CLASS_SYSTEM = 'CBA ClassSystem'
    COL_DESCRIPTION = 'CBA Description'
    COL_DATASET = 'CBA Dataset'
    COL_NOTES = 'CBA Notes'
    COL_STATUS = 'CBA Status'
    COL_EXPLANATION = 'CBA RecordStatusExplanation'
    COL_LINKED_DATA = 'CBA LinkedData'

    properties = {}

    if not _add_type(row, COL_TYPE, Authority, results, properties):
        return

    auth_type = row[COL_TYPE]
    redirect_to = row[COL_REDIRECT] if COL_REDIRECT in row else None
    if redirect_to:
        try:
            Authority.objects.get(pk=redirect_to)
            properties.update({
                'redirect_to_id': redirect_to,
            })
        except Exception as e:
            logger.error(e)
            results.append((ERROR, "Authority does not exist", "", "There exists not authority with id %s. Skipping."%(redirect_to)))
            return

    name = row[COL_NAME] if COL_NAME in row else None
    if name:
        properties.update({
            'name': name,
        })

    first_name = row[COL_FIRST] if COL_FIRST in row else None
    if first_name:
        if auth_type == Authority.PERSON:
            properties.update({
                'personal_name_first': first_name,
            })
        else:
            results.append((WARNING, "Authority is not a person but a %s."%(auth_type), "", "The Authority with name %s is not a person. First name will be ignored."%(name)))

    last_name = row[COL_LAST] if COL_LAST in row else None
    if last_name:
        if auth_type == Authority.PERSON:
            properties.update({
                'personal_name_last': last_name,
            })
        else:
            results.append((WARNING, "Authority is not a person but a %s."%(auth_type), "", "The Authority with name %s is not a person. Last name will be ignored."%(name)))

    suffix = row[COL_SUFFIX] if COL_SUFFIX in row else None
    if suffix:
        if auth_type == Authority.PERSON:
            properties.update({
                'personal_name_suffix': suffix,
            })
        else:
            results.append((WARNING, "Authority is not a person but a %s."%(auth_type), "", "The Authority with name %s is not a person. Suffix will be ignored."%(name)))

    preferred = row[COL_PREFERRED] if COL_PREFERRED in row else None
    if preferred:
        if auth_type == Authority.PERSON:
            properties.update({
                'personal_name_preferred': preferred,
            })
        else:
            results.append((WARNING, "Authority is not a person but a %s."%(auth_type), "", "The Authority with name %s is not a person. Preferred name will be ignored."%(name)))

    
    _add_optional_simple_property(row, COL_CLASS_CODE, properties, 'classification_code')
    _add_optional_simple_property(row, COL_CLASS_HIERARCHY, properties, 'classification_hierarchy')
    _add_optional_simple_property(row, COL_DESCRIPTION, properties, 'description')

    try:
        _add_dataset(row, COL_DATASET, user_id, properties, results)
    except PermissionDenied as e:
        results.append((ERROR, repr(e), "", ""))
        return
    except ObjectDoesNotExist as e:
        results.append((ERROR, "Dataset does not exist.", "", "The dataset %s does not exist."%(row[COL_DATASET])))
        return
    
    _add_classification_system(row, COL_CLASS_SYSTEM, properties, results)
    
    _add_optional_simple_property(row, COL_NOTES, properties, 'administrator_notes')
    _add_status(row, COL_STATUS, properties, results)
    _add_optional_simple_property(row, COL_EXPLANATION, properties, 'record_status_explanation')


    # for whatever reason, no history object is created for authorities
    properties.update({
        'created_by_stored_id': user_id,
        'created_on_stored': created_on.isoformat()
    })

    _add_creation_note(properties, task_id, user_id, created_on)
    if auth_type == Authority.PERSON:
        authority = Person(**properties)
    else:
        authority = Authority(**properties)

    with transaction.atomic():
        _add_tenant(authority, user_id)
        # add new linked data entries if applicable
        linked_data_records, linked_data_identifiers = _add_linked_data(row, COL_LINKED_DATA, authority, results)

        _create_record(authority, user_id, results, alternate_ids=linked_data_identifiers)
        _save_linked_data_authority(linked_data_records, authority)
   

def _add_tenant(record, user_id):
    """
    Method to set the owning tenant of an object. This function assumes that the
    object has an "owning_tenant" property.
    """
    user = User.objects.get(pk=user_id)   
    tenant = c_util.get_tenant(user)
    record.owning_tenant = tenant

def _save_linked_data_authority(linked_data_records, authority):
    """
    Save linked data records with correct authority.
    """
    if linked_data_records:
        # we need to make sure the subjec type is authority, or the generic relations don't work
        authority_obj = Authority.objects.get(pk=authority.id)
        for ld in linked_data_records:
            ld.subject = authority_obj
            ld.save()

def _save_linked_data_citation(linked_data_records, citation):
    """
    Save linked data records with correct citation.
    """
    if linked_data_records:
        # we need to make sure the subjec type is authority, or the generic relations don't work
        for ld in linked_data_records:
            ld.subject = citation
            ld.save()

def _add_linked_data(row, col_type_heading, record, results):
    """
    Function to add linked data entries to an object. Entries should be of the form:
    type::"urn"::"uri"::"description";type::"urn"::"uri"::"description";

    This will not save the created linked data records but instead return them as array for the
    calling function to save them when appropriate.
    """
    if col_type_heading not in row or not row[col_type_heading]:
        return
    
    new_linked_data_entries = []
    new_linked_data_identifiers = []
    items = re.findall('(.+?)::"(.+?)"::"(.*?)"::"(.*?)"', row[col_type_heading])
    
    for item in items:
        ld_type = item[0]
        if not ld_type:
            results.append((ERROR, "No type for linked data entry provided.. Skipping."))
            continue
        linked_data_type = LinkedDataType.objects.filter(name=ld_type).first()
        if not linked_data_type:
            results.append((ERROR, "%s type missing"%(ld_type), "", "There is no linked data type: %s. Skipping."%(ld_type)))
            continue

        urn = item[1]
        uri = item[2]
        description = item[3]

        new_linked_data = LinkedData(type_controlled=linked_data_type, universal_resource_name=urn, url=uri, description=description)
            
        new_linked_data.subject = record
        new_linked_data_entries.append(new_linked_data)

        new_linked_data_identifier = "{0}{1}::{2}".format(LINKED_DATA_PREFIX, ld_type, urn)
        new_linked_data_identifiers.append(new_linked_data_identifier)
        
    return new_linked_data_entries, new_linked_data_identifiers


def _add_type(row, col_type_heading, obj_type, results, properties):
    auth_type = row[col_type_heading]
    if not auth_type:
        results.append((ERROR, "%s type missing"%(obj_type.__name__), "", "There was no %s type provided. Skipping."%(obj_type.__name__)))
        return False

    if auth_type not in list(dict(obj_type.TYPE_CHOICES).keys()):
        results.append((ERROR, "%s type does not exist."%(obj_type.__name__), "", "The %s Type %s does not exist. Skipping."%(obj_type.__name__, auth_type)))
        return False

    properties.update({
        'type_controlled': auth_type,
    })
    return True

def _add_dataset(row, col_dataset_heading, user_id, properties, results):
    dataset = row[col_dataset_heading] if col_dataset_heading in row else None
    if dataset:
        belongs_to = Dataset.objects.filter(name=dataset).first()
        user = User.objects.get(pk=user_id)  

        if not belongs_to:
            raise ObjectDoesNotExist("Dataset does not exist.") 

        if not belongs_to in p_util.get_writable_dataset_objects(user):
            raise PermissionDenied("User cannot write to dataset %s."%belongs_to.name)
        
        properties.update({
            'belongs_to_id': belongs_to.id,
        })
    else:
        raise PermissionDenied("Dataset is missing.")
            

def _add_classification_system(row, col_classsys_heading, properties, results):
    class_system = row[col_classsys_heading] if col_classsys_heading in row else None
    if class_system:
        try:
            classification_system_object = Dataset.objects.filter(name=class_system).first()
            properties.update({
                'classification_system_object_id': classification_system_object.id,
            })
        except:
            results.append((WARNING, "Classification System does not exist.", "", "The classificaiton system %s does not exist."%(class_system)))


def _add_status(row, col_status_heading, properties, results):
    status = row[col_status_heading] if col_status_heading in row else None
    if status:
        status_id = STATUS_MAP.get(status, None)
        if status_id:
            properties.update({
                'record_status_value': status_id
            })
        else:
            properties.update({
                'record_status_value': STATUS_MAP['Inactive']
            })
            results.append((WARNING, "Status does not exist.", "", 'Invalid Status: %s. New record is set to Inactive.'%(status)))

def _add_optional_simple_property(row, col_heading, properties, field_name):
    value = row[col_heading] if col_heading in row else None
    if value:
        properties.update({
            field_name: value,
        })

def _add_creation_note(properties, task_id, user_id, created_on):
    user = User.objects.get(pk=user_id)
    mod_time = created_on.strftime("%m/%d/%y %r %Z")

    properties.update({
        RECORD_HISTORY: "This record was created as part of the bulk creation #%s by %s on %s."%(task_id, user.username, mod_time),
        'modified_by_id': user_id,
    })

def _create_record(record, user_id, results, alternate_ids=[]):
    record.save()
    results.append((SUCCESS, record.id, ", ".join(alternate_ids), 'Added'))
