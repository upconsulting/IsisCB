from isisdata.models import *

from datetime import datetime
from dateutil.tz import tzlocal

STATUS_MAP = {
    'Active': CuratedMixin.ACTIVE,
    'Delete': CuratedMixin.DUPLICATE,
    'Redirect': CuratedMixin.REDIRECT,
    'Inactive': CuratedMixin.INACTIVE
}

SUCCESS = 'SUCCESS'
ERROR = 'ERROR'
WARNING = 'WARNING'

def _create_acrelation(row, user_id, results):
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

    acr_relation = ACRelation(**properties)
    acr_relation._history_user = User.objects.get(pk=user_id)
    acr_relation.save()
    results.append((SUCCESS, acr_relation.id, acr_relation.id, 'Added'))


def _create_ccrelation(row, user_id, results):
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

    ccr_relation = CCRelation(**properties)
    ccr_relation._history_user = User.objects.get(pk=user_id)
    ccr_relation.save()
    results.append((SUCCESS, ccr_relation.id, ccr_relation.id, 'Added'))
