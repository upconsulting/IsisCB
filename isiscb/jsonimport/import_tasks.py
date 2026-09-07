from datetime import datetime

from celery import shared_task
import logging
import haystack

from django.apps import apps
from django.conf import settings
import smart_open, json, csv

from django.contrib.auth.models import User
from django.db import transaction

from jsonimport.models import (
    ImportedAttribute, ImportedAuthority, ImportedAuthorityStatus, ImportedCitation, ImportedACRelation,
    ImportedCCRelation, ImportedCitationStatus, ImportedDataset, ImportedPartDetails,
    ImportedLinkedData
)

from isisdata.models import (
    AsyncTask, ContentType, Attribute, AttributeType, CitationSubtype, ClassificationSystem, LinkedData, 
    Tenant, Authority, Person, Citation, CuratedMixin, ACRelation, CCRelation,
    LinkedDataType
)
from curation import curation_util as cutil


logger = logging.getLogger(__name__)

NEW_RECORD_ACTION = "add new record"

@shared_task
def import_cb_records(task_id, dataset_id, results_path):
    task = AsyncTask.objects.get(pk=task_id)
    dataset = ImportedDataset.objects.get(pk=dataset_id)

    task.state = AsyncTask.STATE_PROCESSING
    task.value = "Creating records from imported data..."
    task.save()

    results = []

    # we have to turn off the signal processor for haystack while we are importing records
    # otherwise it willindex them one at a time which is very slow. 
    # We will re-enable it at the end of the import.
    signal_processor = apps.get_app_config('haystack').signal_processor
    signal_processor.teardown()
    try:
        with transaction.atomic():
            tenant = dataset.owning_tenant
            user = dataset.created_by

            authority_mapping = {} # maps imported authority IDs to new authorities
            citation_mapping = {} # maps imported citation IDs to new citations

            # import authorities
            for imported_authority in ImportedAuthority.objects.filter(dataset=dataset):
                _create_authority(dataset, tenant, user, authority_mapping, imported_authority, results)
            
            # import citations
            for imported_citation in ImportedCitation.objects.filter(dataset=dataset):
                _create_citation(dataset, tenant, user, authority_mapping, citation_mapping, imported_citation, results)

            # once all citations are created, create CCRelations for them
            imported_ccrelations_ids = []
            for imported_citation in ImportedCitation.objects.filter(dataset=dataset):
                for ccrelation in imported_citation.ccrelations.all():
                    if ccrelation.id in imported_ccrelations_ids:
                        continue

                    subject = None
                    object = None
                    if ccrelation.subject == imported_citation:
                        if ccrelation.existing_object:
                            object = ccrelation.existing_object
                        else:
                            object = citation_mapping[ccrelation.object.id]
                        subject = citation_mapping[imported_citation.id]
                    elif ccrelation.object == imported_citation:
                        if ccrelation.existing_subject:
                            subject = ccrelation.existing_subject
                        else:
                            subject = citation_mapping[ccrelation.subject.id]
                        object = citation_mapping[imported_citation.id]

                    CCRelation.objects.create(
                        subject=subject,
                        object=object,
                        type_controlled=ccrelation.type_controlled,
                        data_display_order=ccrelation.data_display_order
                    )
                    imported_ccrelations_ids.append(ccrelation.id)

        task.value = "Indexing citations and authorities..."
        task.save()

        for i, obj in enumerate(Authority.objects.filter(json_import_dataset=dataset)):
            haystack.connections[settings.HAYSTACK_DEFAULT_INDEX].get_unified_index().get_index(Authority).update_object(obj)

        for i, obj in enumerate(Citation.objects.filter(json_import_dataset=dataset)):
            haystack.connections[settings.HAYSTACK_DEFAULT_INDEX].get_unified_index().get_index(Citation).update_object(obj)
                    

        task.state = AsyncTask.STATE_COMPLETED
        task.value = "Import completed successfully."
        task.save()

        dataset.dataset_imported = True
        dataset.save()

        _save_results(results_path, results, ('Local ID', 'CB Id', 'Type', 'Name/Title', 'Message'))
        
    except Exception as e:
        logger.error(f"Error importing dataset {dataset_id}: {str(e)}", exc_info=True)
        task.state = AsyncTask.STATE_FAILED
        task.save()
        dataset.dataset_import_errors = str(e)
        dataset.save()
        return
    finally:
        signal_processor.setup()

def _create_citation(dataset, tenant, user, authority_mapping, citation_mapping, imported_citation, results):
    citation = Citation(
                    title=imported_citation.title,
                    type_controlled=imported_citation.type_controlled,
                    subtype=imported_citation.subtype,
                    modified_by=user,
                    owning_tenant=tenant,
                    physical_details=imported_citation.physical_details,
                    json_import_dataset=dataset,
                    belongs_to=imported_citation.belongs_to
                )
    citation_mapping[imported_citation.id] = citation

    citation.language.add(*imported_citation.language.all())
    citation.save()
    
    _add_record_history_note(citation, imported_citation.local_dataset_id, Citation)
    
    ctype = ContentType.objects.get_for_model(Citation)
    for attribute in imported_citation.get_attributes():
        _create_attribute(attribute, ctype, citation.id)

    # create ACRelations
    for acrelation in imported_citation.acrelations.all():
        if acrelation.existing_authority:
            acrelation_instance = ACRelation.objects.create(
                            citation=citation_mapping[imported_citation.id],
                            authority=acrelation.existing_authority,
                            type_controlled=acrelation.type_controlled,
                            data_display_order=acrelation.data_display_order,
                            name_for_display_in_citation=acrelation.name_for_display_in_citation
                        )
        elif acrelation.authority:
            acrelation_instance = ACRelation.objects.create(
                            citation=citation_mapping[imported_citation.id],
                            authority_id=authority_mapping[acrelation.authority.id].id,
                            type_controlled=acrelation.type_controlled,
                            data_display_order=acrelation.data_display_order,
                            name_for_display_in_citation=acrelation.name_for_display_in_citation
                        )
        
    results.append((imported_citation.local_dataset_id, citation.id, 'Citation', citation.title, 'Created successfully'))   

def _create_authority(dataset, tenant, user, authority_mapping, imported_authority, results):
    if imported_authority.type_controlled == Authority.PERSON:
        authority = Person.objects.create(
                        name=imported_authority.name,
                        type_controlled=imported_authority.type_controlled,
                        personal_name_first=imported_authority.personal_name_first,
                        personal_name_last=imported_authority.personal_name_last,
                        classification_system_object=imported_authority.classification_system_object,
                        modified_by=user,
                        owning_tenant=tenant,
                        json_import_dataset=dataset,
                        belongs_to=imported_authority.belongs_to
                    )
    else: 
        authority = Authority.objects.create(
                        name=imported_authority.name,
                        type_controlled=imported_authority.type_controlled,
                        classification_system_object=imported_authority.classification_system_object,
                        modified_by=user,
                        owning_tenant=tenant,
                        json_import_dataset=dataset,
                        belongs_to=imported_authority.belongs_to
                    )
    
    _add_record_history_note(authority, imported_authority.local_dataset_id, Authority)
    
    authority_mapping[imported_authority.id] = authority

    # get source content type (authority in this case)
    ctype = ContentType.objects.get_for_model(Authority)
    for attribute in imported_authority.get_attributes():
        _create_attribute(attribute, ctype, authority.id)
        
    for linked_data in imported_authority.linkeddata_entries.all():
        linked_data_obj = LinkedData(
                        type_controlled=linked_data.type_controlled,
                        subject_content_type=ctype,
                        subject_instance_id=authority.id,
                        universal_resource_name=linked_data.universal_resource_name
                    )
        linked_data_obj.save()

    results.append((imported_authority.local_dataset_id, authority.id, 'Authority', authority.name, 'Created successfully'))

            
def _create_attribute(attribute, ctype, source_id):
    # content type of value
    vctype = attribute.attribute_type.value_content_type
    avmodel_class = vctype.model_class()

    value_obj = avmodel_class() 
    setattr(value_obj, 'value', attribute.value)
    
    att_init_values = {
        'type_controlled': attribute.attribute_type,
        'source_content_type': ctype,
        'source_instance_id': source_id,
        'value_freeform': attribute.value,
        "value": value_obj
    }

    attribute_obj = Attribute(**att_init_values)
    attribute_obj.save()
    value_obj.attribute = attribute_obj
    value_obj.save()
    return attribute_obj, value_obj

def _add_record_history_note(record, local_id, record_type):
    if record.record_history is None:
        record.record_history = ""
    else:
        record.record_history = record.record_history + "\n"
    
    if record_type == Authority:
        record.record_history = record.record_history + f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Authority record created via JSON import from file {record.json_import_dataset.authority_file_name } for local ID {local_id}."
    elif record_type == Citation:
        record.record_history = record.record_history + f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Citation record created via JSON import from file {record.json_import_dataset.citation_file_name } for local ID {local_id}."
    else:
        record.record_history = record.record_history + f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Record created via JSON import for local ID {local_id}."
    record.save()

def _save_results(path, results, headings):
    with smart_open.smart_open(path, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(headings)
        for result in results:
            writer.writerow(result)