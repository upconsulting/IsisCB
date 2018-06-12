from celery import shared_task

from isisdata.models import *

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist

import logging
import smart_open
import unicodecsv as csv
from datetime import datetime
from dateutil.tz import tzlocal

COLUMN_NAME_ATTR_SUBJ_ID = 'ATT Subj ID'
COLUMN_NAME_ATTR_RELATED_NAME = 'Related Record Name'
COLUMN_NAME_ATTR_TYPE = 'ATT Type'
COLUMN_NAME_ATTR_VALUE = 'ATT Value'
COLUMN_NAME_ATTR_DATE_FREE = 'ATT DateFree'
COLUMN_NAME_ATTR_DATE_BEGIN = 'ATT DateBegin'
COLUMN_NAME_ATTR_DATE_END = 'ATT DateEnd'
COLUMN_NAME_ATTR_PLACE_NAME = 'ATT PlaceName'
COLUMN_NAME_ATTR_PLACE_LINK = 'ATT PlaceLink'
COLUMN_NAME_ATTR_NOTES = 'ATT Notes'

logger = logging.getLogger(__name__)

@shared_task
def add_attributes_to_authority(file_path, error_path, task_id, user_id):
    logging.info('Adding attributes from %s.' % (file_path))
    # this is a hack but the best I can come up with right now :op
    logging.debug('Make AuthorityValue exists in ContentType table...')
    ContentType.objects.get_or_create(model='authorityvalue', app_label='isisdata')

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
        not_matching_subject_names = []

        try:
            for row in csv.DictReader(f):
                subject_id = row[COLUMN_NAME_ATTR_SUBJ_ID]
                try:
                    authority = Authority.objects.get(pk=subject_id)
                except Authority.DoesNotExist:
                    logger.error('Authority with id %s does not exist. Skipping attribute.' % (subject_id))
                    results.append((ERROR, subject_id, subject_id, 'Authority record does not exist.'))
                    current_count = _update_count(current_count, task)
                    continue

                related_name = row[COLUMN_NAME_ATTR_RELATED_NAME]
                if authority.name != related_name:
                    not_matching_subject_names.append((subject_id, authority.name, related_name))

                attribute_type = row[COLUMN_NAME_ATTR_TYPE]

                atype = AttributeType.objects.filter(name=attribute_type)
                if not atype:
                    logger.error('Attribute type with name %s does not exist. Skipping attribute.' % (attribute_type))
                    results.append((ERROR, subject_id, attribute_type, 'Attribute type does not exist.'))
                    current_count = _update_count(current_count, task)
                    continue

                # we can be pretty sure there is just one
                atype = atype.first()
                # get source content type (authority in this case)
                ctype = ContentType.objects.filter(model=type(authority).__name__.lower()).first()

                # content type of value
                vctype = atype.value_content_type
                avmodel_class = vctype.model_class()

                att_init_values = {
                    'type_controlled': atype,
                    'source_content_type': ctype,
                    'source_instance_id': subject_id,
                    'value_freeform': row[COLUMN_NAME_ATTR_DATE_FREE],
                    'administrator_notes': row[COLUMN_NAME_ATTR_NOTES]
                }

                val_init_values = {}
                if row[COLUMN_NAME_ATTR_VALUE]:
                    val_init_values.update({
                        'value': row[COLUMN_NAME_ATTR_VALUE]
                    })

                if row[COLUMN_NAME_ATTR_DATE_BEGIN]:
                    val_init_values.update({
                        'start': ISODateValue.convert(row[COLUMN_NAME_ATTR_DATE_BEGIN])
                    })

                if row[COLUMN_NAME_ATTR_DATE_END]:
                    val_init_values.update({
                        'end': ISODateValue.convert(row[COLUMN_NAME_ATTR_DATE_END])
                    })

                if row[COLUMN_NAME_ATTR_PLACE_NAME]:
                    val_init_values.update({
                        'name': row[COLUMN_NAME_ATTR_PLACE_NAME]
                    })
                    att_init_values['value_freeform'] = row[COLUMN_NAME_ATTR_PLACE_NAME]

                if row[COLUMN_NAME_ATTR_PLACE_LINK]:
                    try:
                        place = Authority.objects.get(pk=row[COLUMN_NAME_ATTR_PLACE_LINK])
                        val_init_values.update({
                            'value': place
                        })
                    except:
                        logger.error('Authority with id %s does not exist.' % (row[COLUMN_NAME_ATTR_PLACE_LINK]))
                        results.append((ERROR, subject_id, row[COLUMN_NAME_ATTR_PLACE_LINK], 'Adding place link. Authority does not exist.'))
                        current_count = _update_count(current_count, task)
                        continue

                attribute = Attribute(**att_init_values)
                attribute.save()
                results.append((SUCCESS, subject_id, attribute.id, 'Added'))

                val_init_values.update({
                    'attribute': attribute
                })

                value = avmodel_class(**val_init_values)
                value.save()

                current_count = _update_count(current_count, task)
        except Exception, e:
            logger.error("There was an unexpected error processing the CSV file.")
            logger.exception(e)
            results.append((ERROR, "unexpected error", "", "There was an unexpected error processing the CSV file: " + repr(e)))

        _save_results(error_path, results)

        task.state = 'SUCCESS'
        task.save()

ELEMENT_TYPES = {
    'Attribute': Attribute,
    'LinkedData': LinkedData,
}

ALLOWED_FIELDS = {
    Attribute: ['description', 'value_freeform', 'value__value', 'record_status_value', 'record_status_explanation'],
    LinkedData: ['description', 'universal_resource_name', 'resource_name', 'url', 'administrator_notes', 'record_status_value', 'record_status_explanation'],
    ACRelation: ['citation_id', 'authority_id', 'name_for_display_in_citation', 'description', 'type_controlled', 'data_display_order', 'confidence_measure','administrator_notes', 'record_status_value', 'record_status_explanation']
}

FIELD_MAP = {
    Attribute: {
        'ATT Description': 'description',
        'ATT Value': 'value__value',
        'ATT Value Freeform': 'value_freeform',
        'ATT Status': 'record_status_value',
        'ATT RecordStatusExplanation': 'record_status_explanation',
        'ATT DateFree': 'value_freeform',
        'ATT DateBegin': 'value__start',
        'ATT DateEnd': 'value__end',
        'ATT PlaceName' : 'value__name',
        'ATT PlaceLink' : 'value__value',
        'ATT Notes': 'administrator_notes',
    },
    LinkedData: {
        'LED URN': 'universal_resource_name',
        'LED URL': 'url',
        'LED Resource': 'resource_name',
        'LED Notes': 'administrator_notes',
        'LED Status': 'record_status_value',
        'LED RecordStatusExplanation': 'record_status_explanation',
    },
    ACRelation: {
        'ACR ID Auth': 'authority_id',
        'ACR ID Cit': 'citation_id',
        'ACR NameDisplay': 'name_for_display_in_citation',
        'ACR Type': 'type_controlled',
        'ACR DataDisplayOrder': 'data_display_order',
        'ACR ConfidenceMeasure': 'confidence_measure',
        'ACR Notes': 'administrator_notes',
        'ACR Status': 'record_status_value',
        'ACR RecordStatusExplanation': 'record_status_explanation',
    }
}

COLUMN_NAME_TYPE = 'Table'
COLUMN_NAME_ID = "Id"
COLUMN_NAME_FIELD = "Field"
COLUMN_NAME_VALUE = "Value"

ADMIN_NOTES = 'administrator_notes'

@shared_task
def update_elements(file_path, error_path, task_id, user_id):
    logging.info('Updating elements from %s.' % (file_path))

    SUCCESS = 'SUCCESS'
    ERROR = 'ERROR'

    result_file_headers = ('Status', 'Type', 'Element Id', 'Message', 'Modification Date')

    with smart_open.smart_open(file_path, 'rb') as f:
        reader = csv.reader(f, encoding='utf-8')
        task = AsyncTask.objects.get(pk=task_id)

        results = []
        row_count = _count_rows(f, results)

        task.max_value = row_count
        task.save()

        current_count = 0

        try:
            current_time = datetime.now(tzlocal()).isoformat()
            for row in csv.DictReader(f):
                # update timestamp for long running processes
                current_time = datetime.now(tzlocal()).isoformat()
                type = row[COLUMN_NAME_TYPE]
                type_class = apps.get_model(app_label='isisdata', model_name=type)
                element_id = row[COLUMN_NAME_ID]

                try:
                    element = type_class.objects.get(pk=element_id)
                except ObjectDoesNotExist:
                    results.append((ERROR, type, element_id, '%s with id %s does not exist.'%(type_class, element_id), current_time))
                    current_count = _update_count(current_count, task)
                    continue

                field_to_change = row[COLUMN_NAME_FIELD]
                new_value = row[COLUMN_NAME_VALUE]

                if field_to_change in FIELD_MAP[type_class]:
                    field_in_csv = field_to_change
                    field_to_change = FIELD_MAP[type_class][field_to_change]
                    # if we change a field that directly belongs to the class
                    if '__' not in field_to_change:
                        # if there are choices make sure they are respected
                        is_valid = _is_value_valid(element, field_to_change, new_value)
                        if not is_valid:
                            results.append((ERROR, type, element_id, '%s is not a valid value.'%(new_value), current_time))
                        else:
                            if field_to_change == ADMIN_NOTES:
                                _add_to_administrator_notes(element, new_value)
                            else:
                                setattr(element, field_to_change, new_value)
                            setattr(element, 'modified_by_id', user_id)
                            _add_change_note(element, task.id, field_in_csv, field_to_change, new_value)
                            element.save()
                            results.append((SUCCESS, element_id, field_in_csv, 'Successfully updated', element.modified_on))
                    # otherwise
                    else:
                        object, field_name = field_to_change.split('__')
                        try:
                            object_to_change = getattr(element, object)
                            object_to_update_timestamp = object_to_change
                            # if we have an attribute, we need to convert the value first
                            if type_class == Attribute:
                                object_to_change = object_to_change.get_child_class()
                                object_to_update_timestamp = element
                                if field_name in ['value', 'start', 'end']:
                                    new_value = object_to_change.__class__.convert(new_value)

                            # if there are choices make sure they are respected
                            is_valid = _is_value_valid(object_to_change, field_name, new_value)
                            if not is_valid:
                                results.append((ERROR, type, element_id, '%s is not a valid value.'%(new_value), current_time))
                            else:
                                if field_to_change == ADMIN_NOTES:
                                    _add_to_administrator_notes(object_to_change, new_value)
                                else:
                                    setattr(object_to_change, field_name, new_value)
                                object_to_change.save()
                                _add_change_note(object_to_update_timestamp, task.id, field_in_csv, field_name, new_value)
                                setattr(object_to_update_timestamp, 'modified_by_id', user_id)
                                object_to_update_timestamp.save()
                                results.append((SUCCESS, element_id, field_in_csv, 'Successfully updated', object_to_update_timestamp.modified_on))
                        except Exception, e:
                            logger.error(e)
                            logger.exception(e)
                            results.append((ERROR, type, element_id, 'Field %s cannot be changed. %s does not exist.'%(field_to_change, object), current_time))

                else:
                    results.append((ERROR, type, element_id, 'Field %s cannot be changed.'%(field_to_change), current_time))

                current_count = _update_count(current_count, task)
        except KeyError, e:
            logger.exception("There was a column error processing the CSV file.")
            results.append((ERROR, "column error", "", "There was a column error processing the CSV file. Have you provided the correct column headers? " + repr(e), current_time))
        except Exception, e:
            logger.error("There was an unexpected error processing the CSV file.")
            logger.exception(e)
            results.append((ERROR, "unexpected error", "", "There was an unexpected error processing the CSV file: " + repr(e), current_time))

        _save_csv_file(error_path, result_file_headers, results)

        task.state = 'SUCCESS'
        task.save()

def _add_to_administrator_notes(element, value):
    note = getattr(element, 'administrator_notes')
    note = note + '\n\n' + value if note else value
    setattr(element, ADMIN_NOTES, note)

def _add_change_note(element, task_nr, field, field_name, value):
    note = getattr(element, ADMIN_NOTES) if getattr(element, ADMIN_NOTES) else ''
    note = note + '\n\nThis record was changed as part of bulk change #%s. "%s" was changed to "%s".'%(task_nr, field, value)
    setattr(element, ADMIN_NOTES, note)

def _is_value_valid(element, field_to_change, new_value):
    choices = element._meta.get_field(field_to_change).choices
    if choices:
        if new_value not in dict(choices):
            return False

    return True

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
        results.append((ERROR, "unexpected error", "", "There was an unexpected error processing the CSV file: " + repr(e)))

    # reset file cursor to first data line
    f.seek(0)

    return row_count

def _save_csv_file(path, headers, data):
    with smart_open.smart_open(path, 'wb') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for line in data:
            writer.writerow(line)

def _save_results(path, results):
    with smart_open.smart_open(path, 'wb') as f:
        writer = csv.writer(f)
        writer.writerow(('Type', 'ATT Subj ID', 'Affected object', 'Message'))
        for result in results:
            writer.writerow(result)
