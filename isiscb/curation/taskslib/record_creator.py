from isisdata.models import *

from datetime import datetime
from dateutil.tz import tzlocal

import logging

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

def _create_linkeddata(row, user_id, results, task_id, created_on):
    COL_LD_URN = 'LED URN'
    COL_LD_STATUS = 'LED Status'
    COL_LD_NOTE = 'LED Note'
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
        except Exception, e:
            logger.error('Related record with id %s does not exist. Skipping attribute.' % (subject_id))
            logger.exception(e)
            results.append((ERROR, subject_id, subject_id, 'Related record does not exist.'))
            return

    if row[COL_LD_URN]:
        properties.update({
            'universal_resource_name': row[COL_LD_URN]
        })

    if row[COL_LD_STATUS]:
        status = row[COL_LD_STATUS]
        status_id = STATUS_MAP[status]
        if status_id:
            properties.update({
                'record_status_value': status_id
            })
        else:
            properties.update({
                'record_status_value': STATUS_MAP['Inactive']
            })
            results.append((ERROR, subject_id, "", 'Invalid Status: %s.'%(status_id)))

    if row[COL_LD_NOTE]:
        properties.update({
            'administrator_notes': row[COL_LD_NOTE]
        })

    if row[COL_LD_RESOURCE]:
        properties.update({
            'resource_name': row[COL_LD_RESOURCE]
        })

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
    COl_ACR_TYPE = 'ACR Type'
    COL_ACR_NAME_DISPLAY = 'ACR NameDisplay'
    COL_ACR_AUTHORITY_ID = 'ACR ID Auth'
    COL_ACR_CITATION_ID = 'ACR ID Cit'
    COL_ACR_DISPLAY_ORDER = 'ACR DataDisplayOrder'
    COL_ACR_CONFIDENCE = 'ACR ConfidenceMeasure'
    COL_ACR_NOTES = 'ACR Notes'
    COL_ACR_STATUS = 'ACR Status'
    COL_ACR_EXPLANATION = 'ACR RecordStatusExplanation'

    properties = {}

    acr_type = row[COl_ACR_TYPE]
    if not acr_type:
        results.append((ERROR, "ACR type missing", "", "There was no ACR type provided. Skipping."))
        return

    if acr_type not in dict(ACRelation.TYPE_CHOICES).keys():
        results.append((ERROR, "ACR type does not exist.", "", "The ACR Type %s does not exist. Skipping."%(acr_type)))
        return

    properties.update({
        'type_controlled': acr_type,
    })

    authority_id = row[COL_ACR_AUTHORITY_ID]
    if not authority_id:
        results.append((ERROR, "Authority missing", "", "There was no authority provided. Skipping."))
        return

    try:
        Authority.objects.get(pk=authority_id)
    except Exception, e:
        logger.error(e)
        results.append((ERROR, "Authority does not exist", "", "There exists not authority with id %s. Skipping."%(authority_id)))
        return

    properties.update({
        'authority_id': authority_id
    })

    citation_id = row[COL_ACR_CITATION_ID]
    if not citation_id:
        results.append((ERROR, "Citation missing", "", "There was no citation provided. Skipping."))
        return

    try:
        Citation.objects.get(pk=citation_id)
    except Exception, e:
        logger.error(e)
        results.append((ERROR, "Citation does not exist", "", "There exists not citation with id %s. Skipping."%(citation_id)))
        return

    properties.update({
        'citation_id': citation_id,
    })

    if row[COL_ACR_NAME_DISPLAY]:
        properties.update({
            'name_for_display_in_citation': row[COL_ACR_NAME_DISPLAY]
        })

    if row[COL_ACR_DISPLAY_ORDER]:
        properties.update({
            'data_display_order': row[COL_ACR_DISPLAY_ORDER]
        })

    if row[COL_ACR_CONFIDENCE]:
        properties.update({
            'confidence_measure': row[COL_ACR_CONFIDENCE]
        })

    if row[COL_ACR_NOTES]:
        properties.update({
            'administrator_notes': row[COL_ACR_NOTES]
        })

    if row[COL_ACR_STATUS]:
        status_id = STATUS_MAP.get(row[COL_ACR_STATUS], None)
        if status_id:
            properties.update({
                'record_status_value': status_id
            })
        else:
            properties.update({
                'record_status_value': STATUS_MAP['Inactive']
            })
            results.append((WARNING, "Status does not exist.", "", 'Invalid Status: %s. New record is set to Inactive.'%(row[COL_ACR_STATUS])))


    if row[COL_ACR_EXPLANATION]:
        properties.update({
            'record_status_explanation': row[COL_ACR_EXPLANATION]
        })

    _add_creation_note(properties, task_id, user_id, created_on)

    acr_relation = ACRelation(**properties)
    _create_record(acr_relation, user_id, results)


def _create_ccrelation(row, user_id, results, task_id, created_on):
    COl_CCR_TYPE = 'CCR Type'
    COL_CCR_OBJECT = 'CCR ID Cit Obj'
    COL_CCR_SUBJECT = 'CCR ID Cit Subj'
    COL_CCR_DISPLAY_ORDER = 'CCR DataDisplayOrder'
    COL_CCR_NOTES = 'ACR Notes'
    COL_CCR_STATUS = 'ACR Status'
    COL_CCR_EXPLANATION = 'ACR RecordStatusExplanation'

    properties = {}

    ccr_type = row[COl_CCR_TYPE]
    if not ccr_type:
        results.append((ERROR, "CCR type missing", "", "There was no CCR type provided. Skipping."))
        return

    if ccr_type not in dict(CCRelation.TYPE_CHOICES).keys():
        results.append((ERROR, "CCR type does not exist.", "", "The CCR Type %s does not exist. Skipping."%(ccr_type)))
        return

    properties.update({
        'type_controlled': ccr_type,
    })

    subject_id = row[COL_CCR_SUBJECT]
    try:
        Citation.objects.get(pk=subject_id)
    except Exception, e:
        logger.error(e)
        results.append((ERROR, "Citation does not exist", "", "There exists not citation with id %s. Skipping."%(subject_id)))
        return

    properties.update({
        'subject_id': subject_id
    })

    object_id = row[COL_CCR_OBJECT]
    try:
        Citation.objects.get(pk=object_id)
    except Exception, e:
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

    if row[COL_CCR_NOTES]:
        properties.update({
            'administrator_notes': row[COL_CCR_NOTES]
        })

    if row[COL_CCR_STATUS]:
        status_id = STATUS_MAP.get(row[COL_CCR_STATUS], None)
        if status_id:
            properties.update({
                'record_status_value': status_id
            })
        else:
            properties.update({
                'record_status_value': STATUS_MAP['Inactive']
            })
            results.append((WARNING, "Status does not exist.", "", 'Invalid Status: %s. New record is set to Inactive.'%(row[COL_CCR_STATUS])))


    if row[COL_CCR_EXPLANATION]:
        properties.update({
            'record_status_explanation': row[COL_CCR_EXPLANATION]
        })

    _add_creation_note(properties, task_id, user_id, created_on)

    ccr_relation = CCRelation(**properties)
    _create_record(ccr_relation, user_id, results)

def _create_authority(row, user_id, results, task_id, created_on):
    COl_TYPE = 'CBA Type'
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

    properties = {}

    auth_type = row[COl_TYPE]
    if not auth_type:
        results.append((ERROR, "Authority type missing", "", "There was no Authority type provided. Skipping."))
        return

    if auth_type not in dict(Authority.TYPE_CHOICES).keys():
        results.append((ERROR, "Authority type does not exist.", "", "The Authority Type %s does not exist. Skipping."%(auth_type)))
        return

    properties.update({
        'type_controlled': auth_type,
    })

    redirect_to = row[COL_REDIRECT]
    if redirect_to:
        try:
            Authority.objects.get(pk=redirect_to)
            properties.update({
                'redirect_to_id': redirect_to,
            })
        except Exception, e:
            logger.error(e)
            results.append((ERROR, "Authority does not exist", "", "There exists not authority with id %s. Skipping."%(redirect_to)))
            return

    name = row[COL_NAME]
    if name:
        properties.update({
            'name': name,
        })

    first_name = row[COL_FIRST]
    if first_name:
        if auth_type == Authority.PERSON:
            properties.update({
                'personal_name_first': first_name,
            })
        else:
            results.append((WARNING, "Authority is not a person but a %s."%(auth_type), "", "The Authority with name %s is not a person. First name will be ignored."%(name)))

    last_name = row[COL_LAST]
    if last_name:
        if auth_type == Authority.PERSON:
            properties.update({
                'personal_name_last': last_name,
            })
        else:
            results.append((WARNING, "Authority is not a person but a %s."%(auth_type), "", "The Authority with name %s is not a person. Last name will be ignored."%(name)))

    suffix = row[COL_SUFFIX]
    if suffix:
        if auth_type == Authority.PERSON:
            properties.update({
                'personal_name_suffix': suffix,
            })
        else:
            results.append((WARNING, "Authority is not a person but a %s."%(auth_type), "", "The Authority with name %s is not a person. Suffix will be ignored."%(name)))

    preferred = row[COL_PREFERRED]
    if preferred:
        if auth_type == Authority.PERSON:
            properties.update({
                'personal_name_preferred': preferred,
            })
        else:
            results.append((WARNING, "Authority is not a person but a %s."%(auth_type), "", "The Authority with name %s is not a person. Preferred name will be ignored."%(name)))

    class_system = row[COL_CLASS_SYSTEM]
    if class_system:
        if class_system not in dict(Authority.CLASS_SYSTEM_CHOICES).keys():
            results.append((WARNING, "Classification System does not exist.", "", "The Classification System %s does not exist."%(class_system)))
        else:
            properties.update({
                'classification_system': class_system,
            })

    class_code = row[COL_CLASS_CODE]
    if class_code:
        properties.update({
            'classification_code': class_code,
        })

    class_hier = row[COL_CLASS_HIERARCHY]
    if class_hier:
        properties.update({
            'classification_hierarchy': class_hier,
        })

    description = row[COL_DESCRIPTION]
    if description:
        properties.update({
            'description': description,
        })

    dataset = row[COL_DATASET]
    if dataset:
        try:
            belongs_to = Dataset.objects.filter(name=dataset).first()
            properties.update({
                'belongs_to_id': belongs_to.id,
            })
        except:
            results.append((WARNING, "Dataset does not exist.", "", "The dataset %s does not exist."%(dataset)))

    notes = row[COL_NOTES]
    if notes:
        properties.update({
            'administrator_notes': notes
        })

    status = row[COL_STATUS]
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

    explain = row[COL_EXPLANATION]
    if explain:
        properties.update({
            'record_status_explanation': explain
        })

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

    _create_record(authority, user_id, results)

def _add_creation_note(properties, task_id, user_id, created_on):
    user = User.objects.get(pk=user_id)
    mod_time = created_on.strftime("%m/%d/%y %r %Z")

    properties.update({
        RECORD_HISTORY: "This record was created as part of the bulk creation #%s by %s on %s."%(task_id, user.username, mod_time),
        'modified_by_id': user_id,
    })

def _create_record(record, user_id, results):
    record.save()
    results.append((SUCCESS, record.id, record.id, 'Added'))
