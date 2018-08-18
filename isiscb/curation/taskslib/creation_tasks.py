from celery import shared_task

from isisdata.models import *

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist

import logging
import smart_open
import record_creator
import unicodecsv as csv
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

logger = logging.getLogger(__name__)

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

        current_time_obj = datetime.now(tzlocal())

        try:
            for row in csv.DictReader(f):
                CREATION_METHODS[record_type](row, user_id, results, task_id, current_time_obj)
                current_count = _update_count(current_count, task)
        except Exception, e:
            logger.error("There was an unexpected error processing the CSV file.")
            logger.exception(e)
            results.append((ERROR, "unexpected error", "", "There was an unexpected error processing the CSV file: " + repr(e)))

        _save_results(error_path, results, ('Type', 'Title', 'Affected object', 'Message'))

        task.state = 'SUCCESS'
        task.save()

CREATION_METHODS =  {
    'acrelation': record_creator._create_acrelation,
    'ccrelation': record_creator._create_ccrelation,
    'linkeddata': record_creator._create_linkeddata,
    'authority': record_creator._create_authority,
    'citation': record_creator._create_citation,
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
