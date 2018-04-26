from celery import shared_task

from isisdata.models import *

import logging
import smart_open
import unicodecsv as csv

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
def add_attributes_to_authority(file_path, error_path, task_id):
    logging.info('Adding attributes from %s.' % (file_path))
    # this is a hack but the best I can come up with right now :op
    logging.debug('Make AuthorityValue exists in ContentType table...')
    ContentType.objects.get_or_create(model='authorityvalue', app_label='isisdata')

    SUCCESS = 'SUCCESS'
    ERROR = 'ERROR'

    with smart_open.smart_open(file_path, 'rb') as f:
        reader = csv.reader(f, encoding='utf-8')
        task = AsyncTask.objects.get(pk=task_id)
        # we want to avoid loading everything in memory, in case it's a large file
        # we do not count the header, so we start at -1
        row_count = -1
        for row in csv.DictReader(f):
            row_count += 1
        task.max_value = row_count
        task.save()
        # reset file cursor to first data line
        f.seek(1)
        current_count = 0
        not_matching_subject_names = []
        results = []
        try:
            for row in csv.DictReader(f):
                subject_id = row[COLUMN_NAME_ATTR_SUBJ_ID]
                try:
                    authority = Authority.objects.get(pk=subject_id)
                except Authority.DoesNotExist:
                    logger.error('Authority with id %s does not exist. Skipping attribute.' % (subject_id))
                    results.append((ERROR, subject_id, subject_id, 'Authority record does not exist.'))
                    current_count = update_count(current_count, task)
                    continue

                related_name = row[COLUMN_NAME_ATTR_RELATED_NAME]
                if authority.name != related_name:
                    not_matching_subject_names.append((subject_id, authority.name, related_name))

                attribute_type = row[COLUMN_NAME_ATTR_TYPE]

                atype = AttributeType.objects.filter(name=attribute_type)
                if not atype:
                    logger.error('Attribute type with name %s does not exist. Skipping attribute.' % (attribute_type))
                    results.append((ERROR, subject_id, attribute_type, 'Attribute type does not exist.'))
                    current_count = update_count(current_count, task)
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
                        current_count = update_count(current_count, task)
                        continue

                attribute = Attribute(**att_init_values)
                attribute.save()
                results.append((SUCCESS, subject_id, attribute.id, 'Added'))

                val_init_values.update({
                    'attribute': attribute
                })

                value = avmodel_class(**val_init_values)
                value.save()

                current_count = update_count(current_count, task)
        except Exception, e:
            logger.error("There was an unexpected error processing the CSV file.")
            logger.exception(e)
            results.append((ERROR, "unexpected error", "", "There was an unexpected error processing the CSV file: " + repr(e)))

        with smart_open.smart_open(error_path, 'wb') as f:
            writer = csv.writer(f)
            writer.writerow(('Type', 'ATT Subj ID', 'Affected object', 'Message'))
            for result in results:
                writer.writerow(result)

        task.state = 'SUCCESS'
        task.save()

def update_count(current_count, task):
    current_count += 1
    task.current_value = current_count
    task.save()
    return current_count
