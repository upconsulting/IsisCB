from __future__ import unicode_literals
from celery import shared_task

from isisdata.models import *
from isisdata.tasks import _get_filtered_object_queryset

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User

import logging
import smart_open
import csv
from datetime import datetime
from dateutil.tz import tzlocal
import time

from past.utils import old_div
import haystack
import math

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
def reindex_authorities(user_id, filter_params_raw, task_id=None, object_type='AUTHORITY'):

    queryset, _ = _get_filtered_object_queryset(filter_params_raw, user_id, object_type)
    if task_id:
        task = AsyncTask.objects.get(pk=task_id)
        task.max_value = queryset.count()
        _inc = max(2, math.floor(old_div(task.max_value, 200.)))
        task.save()
    else:
        task = None
    try:    # Report all exceptions as a task failure.
        for i, obj in enumerate(queryset):
            if task and (i % _inc == 0 or i == (task.max_value - 1)):
                task.current_value = i
                task.save()

            haystack.connections[settings.HAYSTACK_DEFAULT_INDEX].get_unified_index().get_index(Authority).update_object(obj)

        task.state = 'SUCCESS'
        task.save()
    except Exception as E:
        print('bulk_update_citations failed for %s' % filter_params_raw, end=' ')
        print(E)
        task.state = 'FAILURE'
        task.save()

@shared_task
def merge_authorities(file_path, error_path, task_id, user_id):
    logging.info('Merging duplicate authorities and redirecting.')

    SUCCESS = 'SUCCESS'
    ERROR = 'ERROR'

    COL_MASTER_AUTH = 'CBA ID Master'
    COL_DUPLICATE_AUTH = 'CBA ID Duplicate'
    COL_NOTE = 'Note'

    with smart_open.smart_open(file_path, 'rb') as f:
        reader = csv.reader(f, encoding='utf-8')
        task = AsyncTask.objects.get(pk=task_id)

        results = []
        row_count = _count_rows(f, results)

        task.max_value = row_count
        task.save()

        current_count = 0
        not_matching_subject_names = []

        current_time_obj = datetime.now(tzlocal())

        try:
            for row in csv.DictReader(f):
                master_id = row[COL_MASTER_AUTH]
                duplicate_id = row[COL_DUPLICATE_AUTH]
                note = row[COL_NOTE]

                try:
                    master = Authority.objects.get(pk=master_id)
                except Exception as e:
                    logger.error('Authority with id %s does not exist. Skipping.' % (master_id))
                    results.append((ERROR, master_id, 'Authority record does not exist.', ""))
                    current_count = _update_count(current_count, task)
                    continue

                try:
                    duplicate = Authority.objects.get(pk=duplicate_id)
                except Exception as e:
                    logger.error('Authority with id %s does not exist. Skipping.' % (duplicate_id))
                    results.append((ERROR, duplicate_id, 'Authority record does not exist.', ""))
                    current_count = _update_count(current_count, task)
                    continue

                for attr in duplicate.attributes.all():
                    attr.source = master
                    _add_change_note(attr, task_id, 'source', 'source', master_id, duplicate_id, user_id, current_time_obj)
                    attr.record_history += '\n' + note
                    attr.save()

                for ld in duplicate.linkeddata_entries.all():
                    ld.subject = master
                    _add_change_note(ld, task_id, 'source', 'source', master_id, duplicate_id, user_id, current_time_obj)
                    ld.record_history += '\n' + note
                    ld.save()

                for acr in duplicate.acrelations.all():
                    acr.authority = master
                    _add_change_note(acr, task_id, 'source', 'source', master_id, duplicate_id, user_id, current_time_obj)
                    acr.record_history += '\n' + note
                    acr.save()

                # change duplicate record to redirect
                duplicate.redirect_to = master
                old_status = duplicate.record_status_value
                duplicate.record_status_value = CuratedMixin.REDIRECT
                _add_change_note(duplicate, task_id, 'record_status_value', 'record_status_value', "Redirect to %s"%(master_id), old_status, user_id, current_time_obj)
                duplicate.record_history += '\n' + note
                duplicate.save()
                results.append((SUCCESS, "Records Merged", "%s and %s were successfully merged. Master is %s."%(master_id, duplicate_id, master_id), ""))

                current_count = _update_count(current_count, task)
        except Exception as e:
            logger.error("There was an unexpected error processing the CSV file.")
            logger.exception(e)
            results.append((ERROR, "unexpected error", "There was an unexpected error processing the CSV file: " + repr(e), ""))

        _save_results(error_path, results, ('Type', 'Title', 'Message', ''))

        task.state = 'SUCCESS'
        task.save()

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

        current_time_obj = datetime.now(tzlocal())

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

                _add_creation_note(att_init_values, task_id, user_id, current_time_obj)

                attribute = Attribute(**att_init_values)
                attribute.save()
                results.append((SUCCESS, subject_id, attribute.id, 'Added'))

                val_init_values.update({
                    'attribute': attribute
                })

                value = avmodel_class(**val_init_values)
                value.save()

                current_count = _update_count(current_count, task)
        except Exception as e:
            logger.error("There was an unexpected error processing the CSV file.")
            logger.exception(e)
            results.append((ERROR, "unexpected error", "", "There was an unexpected error processing the CSV file: " + repr(e)))

        _save_results(error_path, results, ('Type', 'ATT Subj ID', 'Affected object', 'Message'))

        task.state = 'SUCCESS'
        task.save()

def _add_creation_note(properties, task_id, user_id, created_on):
    user = User.objects.get(pk=user_id)
    mod_time = created_on.strftime("%m/%d/%y %r %Z")

    properties.update({
        RECORD_HISTORY: "This record was created as part of the bulk creation #%s by %s on %s."%(task_id, user.username, mod_time),
        'modified_by_id': user_id,
    })

ELEMENT_TYPES = {
    'Attribute': Attribute,
    'LinkedData': LinkedData,
}

ALLOWED_FIELDS = {
    Attribute: ['description', 'value_freeform', 'value__value', 'record_status_value', 'record_status_explanation'],
    LinkedData: ['description', 'universal_resource_name', 'resource_name', 'url', 'administrator_notes', 'record_status_value', 'record_status_explanation'],
    ACRelation: ['citation_id', 'authority_id', 'name_for_display_in_citation', 'description', 'type_controlled', 'data_display_order', 'confidence_measure','administrator_notes', 'record_status_value', 'record_status_explanation'],
    CCRelation: ['subject_id', 'object_id', 'name', 'description', 'type_controlled', 'belongs_to_id', 'data_display_order', 'administrator_notes', 'record_status_value', 'record_status_explanation']
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
        'LED Subj ID': 'typed:subject',
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
    },
    CCRelation: {
        'CCR ID Cit Subj': 'subject_id',
        'CCR ID Cit Obj': 'object_id',
        'CCR Name': 'name',
        'CCR Description': 'description',
        'CCR Type': 'type_controlled',
        'CCR DisplayOrder': 'data_display_order',
        'CCR Dataset': 'find:Dataset:name:belongs_to',
        'CCR Notes': 'administrator_notes',
        'CCR Status': 'record_status_value',
        'CCR RecordStatusExplanation': 'record_status_explanation',
    },
    Authority: {
        'CBA Type': 'type_controlled',
        'CBA Name': 'name',
        'CBA Redirect': 'redirect_to_id',
        'CBA ClassCode': 'classification_code',
        'CBA ClassHier': 'classification_hierarchy',
        'CBA ClassSystem': 'classification_system',
        'CBA Description': 'description',
        'CBA Dataset': 'find:Dataset:name:belongs_to',
        'CBA Notes': 'administrator_notes',
        'CBA Status': 'record_status_value',
        'CBA RecordStatusExplanation': 'record_status_explanation',
        'CBA First': 'personal_name_first',
        'CBA Last': 'personal_name_last',
        'CBA Suff':  'personal_name_suffix',
        'CBA Preferred': 'personal_name_preferred',
    },
    Citation: {
        'CBB Type': 'type_controlled',
        'CBB Title': 'title',
        'CBB Abstract': 'abstract',
        'CBB Description': 'description',
        'CBB EditionDetails': 'edition_details',
        'CBB Language': 'find:Language:name:language:multi',
        'CBB PhysicalDetails': 'physical_details',
        'CBB IssueBegin':'part_details__issue_begin',
        'CBB IssueEnd': 'part_details__issue_end',
        'CBB IssueFreeText': 'part_details__issue_free_text',
        'CBB PageBegin': 'part_details__page_begin',
        'CBB PageEnd': 'part_details__page_end',
        'CBB PagesFreeText': 'part_details__pages_free_text',
        'CBB VolumeBegin': 'part_details__volume_begin',
        'CBB VolumeEnd': 'part_details__volume_end',
        'CBB VolumeFreeText': 'part_details__volume_free_text',
        'CBB Extent': 'part_details__extent',
        'CBB ExtentNote': 'part_details__extent_note',
        'CBB Dataset': 'find:Dataset:name:belongs_to',
        'CBB Notes': 'administrator_notes',
        'CBB Status': 'record_status_value',
        'CBB RecordStatusExplanation': 'record_status_explanation',
    }
}

COLUMN_NAME_TYPE = 'Table'
COLUMN_NAME_ID = "Id"
COLUMN_NAME_FIELD = "Field"
COLUMN_NAME_VALUE = "Value"

ADMIN_NOTES = 'administrator_notes'
RECORD_HISTORY = 'record_history'

TYPED_PREFIX = 'typed:'
FIND_PREFIX = 'find:'

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
            current_time_obj = datetime.now(tzlocal())
            current_time = current_time_obj.isoformat()
            for row in csv.DictReader(f):
                # update timestamp for long running processes
                current_time = datetime.now(tzlocal()).isoformat()
                elem_type = row[COLUMN_NAME_TYPE]
                element_id = row[COLUMN_NAME_ID]

                try:
                    type_class = apps.get_model(app_label='isisdata', model_name=elem_type)
                except Exception as e:
                    results.append((ERROR, elem_type, element_id, '%s is not a valid type.'%(elem_type), current_time))
                    current_count = _update_count(current_count, task)
                    continue

                try:
                    element = type_class.objects.get(pk=element_id)
                    # we need special handling of persons, this is ugly but ahh well
                    if elem_type == "Authority" and element.type_controlled == Authority.PERSON:
                        element = Person.objects.get(pk=element_id)
                except ObjectDoesNotExist:
                    results.append((ERROR, elem_type, element_id, '%s with id %s does not exist.'%(type_class, element_id), current_time))
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
                            results.append((ERROR, elem_type, element_id, '%s is not a valid value.'%(new_value), current_time))
                        else:
                            try:
                                if field_to_change == ADMIN_NOTES:
                                    _add_to_administrator_notes(element, new_value, task.id, user_id, current_time_obj)
                                else:
                                    # in some cases we have authority or citation as relation
                                    # this is in cases like subject of linkeddata
                                    # it needs to be amended if there are objects that can link to other types
                                    # than authorities/citations
                                    if field_to_change.startswith(TYPED_PREFIX):
                                        field_to_change = field_to_change[len(TYPED_PREFIX):]
                                        if new_value.startswith(Authority.ID_PREFIX):
                                            linked_element = Authority.objects.get(pk=new_value)
                                        else:
                                            linked_element = Citation.objects.get(pk=new_value)
                                        new_value = linked_element

                                    if field_to_change.startswith(FIND_PREFIX):
                                        field_to_change, new_value = _find_value(field_to_change, new_value, element)

                                    old_value = getattr(element, field_to_change)
                                    setattr(element, field_to_change, new_value)

                                    # some fields need special handling
                                    _specific_post_processing(element, field_to_change, new_value, old_value)

                                    _add_change_note(element, task.id, field_in_csv, field_to_change, new_value, old_value, user_id, current_time_obj)
                                setattr(element, 'modified_by_id', user_id)

                                element.save()
                                results.append((SUCCESS, element_id, field_in_csv, 'Successfully updated', element.modified_on))
                            except Exception as e:
                                logger.error(e)
                                logger.exception(e)
                                results.append((ERROR, elem_type, element_id, 'Something went wrong. %s was not changed.'%(field_to_change), current_time))
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
                            # this is a hack, but ahh well
                            if type(object_to_change) == PartDetails:
                                object_to_update_timestamp = element

                            # if there are choices make sure they are respected
                            is_valid = _is_value_valid(object_to_change, field_name, new_value)
                            if not is_valid:
                                results.append((ERROR, elem_type, element_id, '%s is not a valid value.'%(new_value), current_time))
                            else:
                                old_value = getattr(object_to_change, field_name)
                                if field_to_change == ADMIN_NOTES:
                                    _add_to_administrator_notes(object_to_change, new_value, task.id, user_id, current_time_obj)
                                    old_value = old_value[:10] + "..."
                                else:
                                    setattr(object_to_change, field_name, new_value)
                                object_to_change.save()
                                _add_change_note(object_to_update_timestamp, task.id, field_in_csv, field_name, new_value, old_value, user_id, current_time_obj)
                                setattr(object_to_update_timestamp, 'modified_by_id', user_id)
                                object_to_update_timestamp.save()
                                results.append((SUCCESS, element_id, field_in_csv, 'Successfully updated', object_to_update_timestamp.modified_on))
                        except Exception as e:
                            logger.error(e)
                            logger.exception(e)
                            results.append((ERROR, type, element_id, 'Field %s cannot be changed. %s does not exist.'%(field_to_change, object), current_time))

                else:
                    results.append((ERROR, elem_type, element_id, 'Field %s cannot be changed.'%(field_to_change), current_time))

                current_count = _update_count(current_count, task)
        except KeyError as e:
            logger.exception("There was a column error processing the CSV file.")
            results.append((ERROR, "column error", "", "There was a column error processing the CSV file. Have you provided the correct column headers? " + repr(e), current_time))
        except Exception as e:
            logger.error("There was an unexpected error processing the CSV file.")
            logger.exception(e)
            results.append((ERROR, "unexpected error", "", "There was an unexpected error processing the CSV file: " + repr(e), current_time))

        _save_csv_file(error_path, result_file_headers, results)

        task.state = 'SUCCESS'
        task.save()

def _specific_post_processing(element, field_name, new_value, old_value):
    # turn authority non-person into person
    if type(element) == Authority and field_name == 'type_controlled':
        if new_value == Authority.PERSON and old_value != Authority.PERSON:
            try:
                # is object already a person
                element.person
            except Person.DoesNotExist:
                # if not make it one
                person = Person(authority_ptr_id=element.pk)
                person.__dict__.update(element.__dict__)
                person.save()
    if type(element) == Citation and field_name == 'type_controlled':
        if new_value in [Citation.ARTICLE, Citation.BOOK, Citation.REVIEW, Citation.CHAPTER, Citation.THESIS]:
            if not hasattr(element, 'part_details'):
                element.part_details = PartDetails()


# to specify a find operation, fields need to be in format find:type:field:linking_field (e.g. find:Dataset:name:belongs_to_id)
def _find_value(field_to_change, new_value, element):
    field_parts = field_to_change.split(":")
    model = apps.get_model("isisdata." + field_parts[1])
    filter_params = { field_parts[2]:new_value }
    linked_element = model.objects.filter(**filter_params).first()
    if len(field_parts) > 4:
        if field_parts[4] == "multi":
            old_value = getattr(element, field_parts[3])
            linked_element = list(old_value.all()) + [linked_element]
    return field_parts[3], linked_element


def _add_to_administrator_notes(element, value, task_nr,  modified_by, modified_on):
    note = getattr(element, ADMIN_NOTES)
    if note:
        note += '\n\n'
    user = User.objects.get(pk=modified_by)
    mod_time = modified_on.strftime("%m/%d/%y %r %Z")
    note += "%s added the following in bulk change #%s on %s:"%(user.username, task_nr, mod_time)
    note += '\n'
    note += value
    setattr(element, ADMIN_NOTES, note)

def _add_change_note(element, task_nr, field, field_name, value, old_value, modified_by, modified_on):
    user = User.objects.get(pk=modified_by)
    mod_time = modified_on.strftime("%m/%d/%y %r %Z")
    note = getattr(element, RECORD_HISTORY) + '\n\n' if getattr(element, RECORD_HISTORY) else ''
    note += 'This record was changed as part of bulk change #%s. "%s" was changed from "%s" to "%s" by %s on %s.'%(task_nr, field, old_value, value, user.username, mod_time)
    setattr(element, RECORD_HISTORY, note)

    element._history_user=user

def _is_value_valid(element, field_to_change, new_value):
    if ":" in field_to_change:
        return True
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
    except Exception as e:
        logger.error("There was an unexpected error processing the CSV file.")
        logger.exception(e)
        results.append(('ERROR', "unexpected error", "", "There was an unexpected error processing the CSV file: " + repr(e)))

    # reset file cursor to first data line
    f.seek(0)

    return row_count

def _save_csv_file(path, headers, data):
    with smart_open.smart_open(path, 'wb') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for line in data:
            writer.writerow(line)

def _save_results(path, results, headings):
    with smart_open.smart_open(path, 'wb') as f:
        writer = csv.writer(f)
        writer.writerow(headings)
        for result in results:
            writer.writerow(result)
