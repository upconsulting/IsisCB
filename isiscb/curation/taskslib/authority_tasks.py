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
def add_attributes_to_authority(file_path, task_id):
    logging.info('Adding attributes from %s.' % (file_path))
    # this is a hack but the best I can come up with right now :op
    logging.debug('Make AuthorityValue exists in ContentType table...')
    ContentType.objects.get_or_create(model='authorityvalue', app_label='isisdata')

    with smart_open.smart_open(file_path, 'r') as f:
        reader = csv.reader(f)
        task = AsyncTask.objects.get(pk=task_id)
        # we want to avoid loading everything in memory, in case it's a large file
        # we do not count the header, so we start at -1
        row_count = -1
        for row in csv.reader(f):
            row_count += 1
        task.max_value = row_count
        # reset file cursor to first data line
        f.seek(1)
        current_count = 0
        not_matching_subject_names = []
        errors = []
        for row in csv.DictReader(f):
            subject_id = row[COLUMN_NAME_ATTR_SUBJ_ID]
            try:
                authority = Authority.objects.get(pk=subject_id)
            except DoesNotExist:
                logger.error('Authority with id %s does not exist. Skipping attribute.' % (subject_id))
                errors.append((subject_id, subject_id, 'Authority record does not exist.'))
                current_count += 1
                task.current_value = current_count
                continue

            related_name = row[COLUMN_NAME_ATTR_RELATED_NAME]
            if authority.name != related_name:
                not_matching_subject_names.append((subject_id, authority.name, related_name))

            attribute_type = row[COLUMN_NAME_ATTR_TYPE]

            atype = AttributeType.objects.filter(name=attribute_type)
            if not atype:
                logger.error('Attribute type with name %s does not exist. Skipping attribute.' % (attribute_type))
                errors.append((subject_id, attribute_type, 'Attribute type does not exist.'))
                current_count += 1
                task.current_value = current_count
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
            attribute = Attribute(**att_init_values)
            attribute.save()

            val_init_values = {
                'attribute': attribute
            }

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

            if row[COLUMN_NAME_ATTR_PLACE_LINK]:
                try:
                    place = Authority.objects.get(pk=row[COLUMN_NAME_ATTR_PLACE_LINK])
                    val_init_values.update({
                        'value': place
                    })
                except:
                    logger.error('Authority with id %s does not exist.' % (row[COLUMN_NAME_ATTR_PLACE_LINK]))
                    errors.append((subject_id, row[COLUMN_NAME_ATTR_PLACE_LINK], 'Authority does not exist.'))


            print val_init_values
            value = avmodel_class(**val_init_values)
            value.save()
