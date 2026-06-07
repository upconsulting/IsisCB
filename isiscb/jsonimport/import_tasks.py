from datetime import datetime

from celery import shared_task
import logging

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
def import_cb_records(task_id, dataset_id):
    task = AsyncTask.objects.get(pk=task_id)
    dataset = ImportedDataset.objects.get(pk=dataset_id)

    task.state = AsyncTask.STATE_PROCESSING
    task.save()

    try:
        with transaction.atomic():
            tenant = dataset.owning_tenant
            user = dataset.created_by

            authority_mapping = {} # maps imported authority IDs to new authorities
            citation_mapping = {} # maps imported citation IDs to new citations

            # import authorities
            for imported_authority in ImportedAuthority.objects.filter(dataset=dataset):
                if imported_authority.type_controlled == Authority.PERSON:
                    authority = Person.objects.create(
                        name=imported_authority.name,
                        type_controlled=imported_authority.type_controlled,
                        personal_name_first=imported_authority.personal_name_first,
                        personal_name_last=imported_authority.personal_name_last,
                        classification_system_object=imported_authority.classification_system_object,
                        modified_by=user,
                        owning_tenant=tenant,
                        json_import_dataset=dataset
                    )
                else: 
                    authority = Authority.objects.create(
                        name=imported_authority.name,
                        type_controlled=imported_authority.type_controlled,
                        classification_system_object=imported_authority.classification_system_object,
                        modified_by=user,
                        owning_tenant=tenant,
                        json_import_dataset=dataset
                    )

                authority_mapping[imported_authority.id] = authority

                # get source content type (authority in this case)
                ctype = ContentType.objects.get_for_model(Authority)
                for attribute in imported_authority.get_attributes():
                    _create_attribute(attribute, ctype, authority.id)

                for linked_data in imported_authority.linkeddata_entries.all():
                    linked_data_obj = LinkedData.objects.create(
                        type_controlled=linked_data.type_controlled,
                        subject_content_type=ctype,
                        subject_instance_id=authority.id,
                        universal_resource_name=linked_data.universal_resource_name
                    )
                    linked_data_obj.save()

            # import citations
            for imported_citation in ImportedCitation.objects.filter(dataset=dataset):
                
                citation = Citation.objects.create(
                    title=imported_citation.title,
                    type_controlled=imported_citation.type_controlled,
                    subtype=imported_citation.subtype,
                    modified_by=user,
                    owning_tenant=tenant,
                    physical_details=imported_citation.physical_details,
                    json_import_dataset=dataset
                )
                citation_mapping[imported_citation.id] = citation

                citation.language.add(*imported_citation.language.all())
                citation.save()

                ctype = ContentType.objects.get_for_model(Citation)
                for attribute in imported_citation.get_attributes():
                    _create_attribute(attribute, ctype, citation.id)

                # create ACRelations
                for acrelation in imported_citation.acrelations.all():
                    if acrelation.existing_authority:
                        ACRelation.objects.create(
                            citation=citation_mapping[imported_citation.id],
                            authority=acrelation.existing_authority,
                            type_controlled=acrelation.type_controlled,
                            data_display_order=acrelation.data_display_order,
                            name_for_display_in_citation=acrelation.name_for_display_in_citation
                        )
                    elif acrelation.authority:
                        ACRelation.objects.create(
                            citation=citation_mapping[imported_citation.id],
                            authority=authority_mapping[acrelation.authority.id],
                            type_controlled=acrelation.type_controlled,
                            data_display_order=acrelation.data_display_order,
                            name_for_display_in_citation=acrelation.name_for_display_in_citation
                        )
            task.state = AsyncTask.STATE_COMPLETED
            task.save()

            dataset.dataset_imported = True
            dataset.save()
    except Exception as e:
        logger.error(f"Error importing dataset {dataset_id}: {str(e)}")
        task.state = AsyncTask.STATE_FAILED
        task.save()
        dataset.dataset_import_errors = str(e)
        dataset.save()
        return
            
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