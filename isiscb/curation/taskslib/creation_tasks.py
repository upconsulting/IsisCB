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

logger = logging.getLogger(__name__)

@shared_task
def create_linked_data(file_path, error_path, task_id, user_id):
    logging.info('Creating records from %s.' % (file_path))

    SUCCESS = 'SUCCESS'
    ERROR = 'ERROR'

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
                        results.append((ERROR, authority_id, authority_id, "Authority name (%s) and provided name (%s) do not match."%(authority.name, auth_name)))

                linked_data = LinkedData(**properties)
                linked_data.save()
                results.append((SUCCESS, authority_id, linked_data.id, 'Added'))


        except Exception, e:
            logger.error("There was an unexpected error processing the CSV file.")
            logger.exception(e)
            results.append((ERROR, "unexpected error", "", "There was an unexpected error processing the CSV file: " + repr(e)))

        _save_results(error_path, results)

        task.state = 'SUCCESS'
        task.save()


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

def _save_results(path, results):
    with smart_open.smart_open(path, 'wb') as f:
        writer = csv.writer(f)
        writer.writerow(('Type', 'LD Subj ID', 'Affected object', 'Message'))
        for result in results:
            writer.writerow(result)
