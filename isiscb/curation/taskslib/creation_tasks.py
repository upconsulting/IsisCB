from celery import shared_task

from isisdata.models import *

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist

import logging
import smart_open
import unicodecsv as csv
from datetime import datetime
from dateutil.tz import tzlocal


COL_LD_URN = 'LED URN'
COL_LD_STATUS = 'LED Status'
COL_LD_NOTE = 'LED Note'
COL_LD_RESOURCE = 'LED Resource'
COL_LD_AUTHORITY = 'LED Subj ID'
COL_LD_TYPE = 'LED Type'
COL_AUTH_NAME = 'CBA Name'

STATUS_MAP = {
    'Active': CuratedMixin.ACTIVE,
    'Delete': CuratedMixin.DUPLICATE,
    'Redirect': CuratedMixin.REDIRECT,
    'Inactive': CuratedMixin.INACTIVE
}

SUCCESS = 'SUCCESS'
ERROR = 'ERROR'
WARNING = 'WARNING'

logger = logging.getLogger(__name__)

@shared_task
def create_linked_data(file_path, error_path, task_id, user_id):
    logging.info('Creating records from %s.' % (file_path))


    with smart_open.smart_open(file_path, 'rb') as f:
        reader = csv.reader(f, encoding='utf-8')
        task = AsyncTask.objects.get(pk=task_id)

        results = []
        row_count = _count_rows(f, results)

        task.max_value = row_count
        task.save()

        current_count = 0
        not_matching = []

        try:
            for row in csv.DictReader(f):
                properties = {}

                if not row[COL_LD_AUTHORITY]:
                    results.append((ERROR, "Authority missing", "", "There was no authority provided."))
                    current_count = _update_count(current_count, task)
                    continue
                else:
                    authority_id = row[COL_LD_AUTHORITY]
                    try:
                        authority = Authority.objects.get(pk=authority_id)
                        properties.update({
                            'subject': authority
                        })
                    except Authority.DoesNotExist:
                        logger.error('Authority with id %s does not exist. Skipping attribute.' % (authority_id))
                        results.append((ERROR, authority_id, authority_id, 'Authority record does not exist.'))
                        current_count = _update_count(current_count, task)
                        continue

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
                        results.append((ERROR, authority_id, "", 'Invalid Status: %s.'%(status_id)))

                if row[COL_LD_NOTE]:
                    properties.update({
                        'administrator_notes': row[COL_LD_NOTE]
                    })

                if row[COL_LD_RESOURCE]:
                    properties.update({
                        'resource_name': row[COL_LD_RESOURCE]
                    })

                if row[COL_LD_TYPE]:
                    type = row[COL_LD_TYPE]
                    type_obj = LinkedDataType.objects.filter(name=type).first()
                    if type_obj:
                        properties.update({
                            'type_controlled_id': type_obj.pk
                        })
                    else:
                        results.append((ERROR, authority_id, authority_id, "Object type does not exist: " + type))
                        logger.error('Linked Data Type %s does not exist. Skipping linked data.' % (type))
                        current_count = _update_count(current_count, task)
                        continue

                if row[COL_AUTH_NAME]:
                    auth_name = row[COL_AUTH_NAME]
                    # check authority name
                    if auth_name != authority.name:
                        results.append((WARNING, authority_id, authority_id, "Authority name (%s) and provided name (%s) do not match."%(authority.name, auth_name)))

                linked_data = LinkedData(**properties)
                linked_data._history_user = User.objects.get(pk=user_id)
                linked_data.save()
                results.append((SUCCESS, authority_id, linked_data.id, 'Added'))


        except Exception, e:
            logger.error("There was an unexpected error processing the CSV file.")
            logger.exception(e)
            results.append((ERROR, "unexpected error", "", "There was an unexpected error processing the CSV file: " + repr(e)))

        _save_results(error_path, results, ('Type', 'LD Subj ID', 'Affected object', 'Message'))

        task.state = 'SUCCESS'
        task.save()



@shared_task
def create_records(file_path, error_path, task_id, user_id, record_type):
    logging.info('Creating records from %s.' % (file_path))

    with smart_open.smart_open(file_path, 'rb') as f:
        reader = csv.reader(f, encoding='utf-8')
        task = AsyncTask.objects.get(pk=task_id)

        results = []
        row_count = _count_rows(f, results)

        task.max_value = row_count
        task.save()

        current_count = 0
        not_matching = []

        try:
            for row in csv.DictReader(f):
                CREATION_METHODS[record_type](row, user_id, results)
                current_count = _update_count(current_count, task)
        except Exception, e:
            logger.error("There was an unexpected error processing the CSV file.")
            logger.exception(e)
            results.append((ERROR, "unexpected error", "", "There was an unexpected error processing the CSV file: " + repr(e)))

        _save_results(error_path, results, ('Type', 'Title', 'Affected object', 'Message'))

        task.state = 'SUCCESS'
        task.save()

def _create_acrelation(row, user_id, results):
    COl_ACR_TYPE = 'ACR Type'
    COL_ACR_NAME_DIESPLAY = 'ACR NameDisplay'
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

    if row[COL_ACR_NAME_DIESPLAY]:
        properties.update({
            'name_for_display_in_citation': row[COL_ACR_NAME_DIESPLAY]
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

CREATION_METHODS =  {
    'acrelation': _create_acrelation,
}

def _update_count(current_count, task):
    current_count += 1
    task.current_value = current_count
    task.save()
    return current_count

def _count_rows(f, results):
    # we want to avoid loading everything in memory, in case it's a large file
    # we do not count the header, so we start at -1
    row_count = -1
    try:
        for row in csv.DictReader(f):
            row_count += 1
    except Exception, e:
        logger.error("There was an unexpected error processing the CSV file.")
        logger.exception(e)
        results.append(('ERROR', "unexpected error", "", "There was an unexpected error processing the CSV file: " + repr(e)))

    # reset file cursor to first data line
    f.seek(0)

    return row_count

def _save_results(path, results, headings):
    with smart_open.smart_open(path, 'wb') as f:
        writer = csv.writer(f)
        writer.writerow(headings)
        for result in results:
            writer.writerow(result)
