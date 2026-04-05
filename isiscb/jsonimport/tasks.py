from celery import shared_task
import logging

import smart_open, json, csv

from django.contrib.auth.models import User
from jsonimport.models import (
    ImportedAuthority, ImportedCitation, ImportedACRelation,
    ImportedCCRelation, ImportedDataset, ImportedPartDetails,
    ImportedLinkedData
)

from isisdata.models import (
    AsyncTask, AttributeType, CitationSubtype, ClassificationSystem, 
    Tenant, Authority, Citation, CuratedMixin, ACRelation, CCRelation,
    LinkedDataType
)
from curation import curation_util as cutil


logger = logging.getLogger(__name__)

@shared_task
def import_records(file_path, error_path, task_id, user_id):
   
    logging.info('Importing JSON records from %s.' % file_path)

    SUCCESS = 'SUCCESS'
    ERROR = 'ERROR'
    WARNING = 'WARNING'

    task = None
    try:
        task = AsyncTask.objects.get(pk=task_id)
    except Exception:
        logging.exception('Could not find AsyncTask with id %s' % task_id)
        return

    task.state = 'PROCESSING'
    task.save()

    results = []
  
    tenant = cutil.get_tenant(User.objects.filter(pk=user_id).first())
    if not tenant:
        logging.exception('Could not find Tenant for user %s' % user_id)
        results.append((ERROR, 'User', user_id, 'Could not find tenant for user'))
        _save_results(error_path, results, ('Type', 'Title', 'Ids', 'Message'))
        if task:
            task.state = 'ERROR'
            task.save()
        return

    
    # read JSON
    try:
        with smart_open.smart_open(file_path, 'r') as f:
            content = f.read()
            data = json.loads(content)
    except Exception as e:
        logging.exception(e)
        results.append((ERROR, 'file', '', 'Could not read or parse JSON: %s' % repr(e)))
        _save_results(error_path, results, ('Type', 'Title', 'Ids', 'Message'))
        if task:
            task.state = 'ERROR'
            task.save()
        return
    
    dataset = _create_dataset(user_id, tenant, task, data.get('dataset') or {})

    authorities = []
    citations = []

    items = data.get('records') or []
    for item in items:
        if 'record_type' in item and item['record_type'] == 'authority':
            authorities.append(item)
        elif 'record_type' in item and item['record_type'] == 'citation':
            citations.append(item)
        else:
            results.append((ERROR, 'Record', item.get('id') or '', 'Missing or invalid record_type field'))

    total = len(authorities) + len(citations)
    if task:
        task.max_value = total
        task.current_value = 0
        task.save()

    # maps from local id to created instance
    auth_map = {}
    cit_map = {}

    user = User.objects.filter(username=user_id).first()
    
    # create authorities
    for authority_info in authorities:
        _create_imported_authority(user, task, tenant, results, dataset, auth_map, authority_info)
        

    # create citations
    for citation_data in citations:
        citation = _create_imported_citation(task, tenant, results, dataset, cit_map, citation_data)
        if citation:
            for ac_data in citation_data.get('related_authorities') or []:
                _create_ac_relation(ac_data, auth_map, citation, results)
        else:
            results.append((ERROR, 'Citation', citation_data.get('local_dataset_id') or '', 'Failed to create citation, so related authorities could not be linked.'))
            
        # TODO: ccrelations


    # write results
    _save_results(error_path, results, ('Type', 'Title', 'Ids', 'Message'))

    if task:
        task.state = 'SUCCESS'
        task.save()

def _create_imported_citation(task, tenant, results, dataset, cit_map, citation_data):
    try:
        title = citation_data.get('title') or ''
        local_id = citation_data.get('local_dataset_id')
        
        type_controlled = _get_citation_type(citation_data.get('citation_type'))
        if not type_controlled:
            results.append(('ERROR', 'Citation', local_id, f'Missing or invalid citation type: {citation_data.get("citation_type")}'))
            return None

        subtype = None
        if citation_data.get('subtype_name'):
            subtype = CitationSubtype.objects.filter(name=citation_data.get('subtype_name')).first()
            if not subtype:
                results.append(('WARNING', 'Citation', local_id, f'Invalid citation subtype: {citation_data.get("subtype_name")}'))
            else:
                if subtype.related_citation_type != type_controlled:
                    results.append(('WARNING', 'Citation', local_id, f'Citation subtype {citation_data.get("subtype_name")} is not a subtype of citation type {citation_data.get("type_controlled")}'))  
                    subtype = None      
            
        cit = ImportedCitation.objects.create(
            dataset=dataset,
            local_dataset_id=local_id,
            title=title,
            complete_citation=citation_data.get('full_citation') or '',
            subtype=subtype,
            description=citation_data.get('description') or '',
            type_controlled=type_controlled,
            abstract=citation_data.get('abstract') or '',
            edition_details=citation_data.get('edition_details') or '',
            physical_details=citation_data.get('physical_details') or '',
        )

        # part details
        part = citation_data.get('part_details') or None
        if part:
            pd = ImportedPartDetails.objects.create(
                    volume=part.get('volume'),
                    volume_free_text=part.get('volume_free_text'),
                    volume_begin=part.get('volume_begin'),
                    volume_end=part.get('volume_end'),
                    issue_free_text=part.get('issue_free_text'),
                    issue_begin=part.get('issue_begin'),
                    issue_end=part.get('issue_end'),
                    pages_free_text=part.get('pages_free_text'),
                    page_begin=part.get('page_begin'),
                    page_end=part.get('page_end'),
                    extent=part.get('extent'),
                    extent_note=part.get('extent_note')
                )
            pd.save()
            cit.part_details = pd
        
        for attr in citation_data.get('attributes') or []:
            attribute = _create_attribute(attr.get('type'), attr.get('value'))
            if attribute:
                cit.attributes.add(attribute)

        cit.save()

        for linked_data in citation_data.get('linked_data') or []:
            _create_linkeddata(linked_data, cit)

        cit_map[local_id] = cit

        results.append(('SUCCESS', 'Citation', f"{local_id}: {title}", 'Created'))

        if task:
            task.current_value = task.current_value + 1
            task.save()

        return cit
    except Exception as e:
        logging.exception(e)
        results.append(('ERROR', 'Citation', citation_data.get('id') or '', 'Error creating citation: %s' % repr(e)))
        return None

def _get_citation_type(cit_type):
    resource_types = {
        "book": Citation.BOOK,
        "article": Citation.ARTICLE,
        "chapter": Citation.CHAPTER,
        "review": Citation.REVIEW,
        "essay review": Citation.ESSAY_REVIEW,
        "thesis": Citation.THESIS,
        "event": Citation.EVENT,
        "web object": Citation.WEB_OBJECT,
        "multimedia object": Citation.MULTIMEDIA_OBJECT,
        "archive object": Citation.ARCHIVE_OBJECT,
        "digital resource": Citation.DIGITAL_RESOURCE,
        "personal recognition": Citation.PERSONAL_RECOGNITION,
        "presentation": Citation.PRESENTATION,
        "interactive": Citation.INTERACTIVE,
        "website": Citation.WEBSITE,
        "application": Citation.APPLICATION
    }
    return resource_types.get(cit_type.lower(), "")

def _create_imported_authority(user, task, tenant, results, dataset, auth_map, authority_data):
    try:
        name = authority_data.get('name', '')
        type_controlled = _get_authority_type(authority_data.get('authority_type'))
        local_dataset_id = authority_data.get('local_dataset_id') or ''
        
        if not type_controlled:
            results.append(('ERROR', 'Authority', local_dataset_id, f'Missing or invalid authority type: {authority_data.get("authority_type")}'))
            return None
        
        if authority_data.get('classification_system_name'):
            class_system =_get_classifcation_system(user, authority_data.get('classification_system_name'))
        else:
            class_system =_get_default_classification_system(user, type_controlled)
            print(f'No classification system specified for authority {name} with local id {local_dataset_id}. Using default classification system {class_system} for authority type {type_controlled}.')
        if not class_system:
            results.append(('ERROR', 'Authority', local_dataset_id, f'Invalid classification system or no default classification system: {authority_data.get("classification_system_name")}'))
            return None
        
        auth = ImportedAuthority.objects.create(
                name=name,
                local_dataset_id=local_dataset_id,
                dataset=dataset,
                description=authority_data.get('description') or '',
                type_controlled=type_controlled,
                classification_system_object=class_system,
                classification_code=authority_data.get('classification_code') or '',
                record_status=_get_authority_record_status(authority_data.get('record_status', "inactive")),
                personal_name_last=authority_data.get('personal_name_last') or '',
                personal_name_first=authority_data.get('personal_name_first') or '',
                personal_name_suffix=authority_data.get('personal_name_suffix') or '',
                personal_name_preferred=authority_data.get('personal_name_preferred') or '',
            )

        for attr in authority_data.get('attributes') or []:
            attribute = _create_attribute(attr.get('type'), attr.get('value'))
            if attribute:
                auth.attributes.add(attribute)

        auth.save()

        for linked_data in authority_data.get('linked_data') or []:
            _create_linkeddata(linked_data, auth)

        auth_map[local_dataset_id] = auth

        results.append(('SUCCESS', 'Authority', local_dataset_id or '', 'Created'))
    except Exception as e:
        logging.exception(e)
        results.append(('ERROR', 'Authority', authority_data.get('local_dataset_id') or '', 'Error creating authority: %s' % repr(e)))
    if task:
        task.current_value = task.current_value + 1
        task.save()

def _create_dataset(user_id, tenant, task, dataset_info):
    user = User.objects.filter(pk=user_id).first()
    dataset = ImportedDataset.objects.create(
        name=dataset_info.get('dataset_name'),
        owning_tenant=tenant,
        created_by=user,
        description=dataset_info.get('dataset_description'),
        dataset_id=dataset_info.get('dataset_id'),
        dataset_creator=dataset_info.get('dataset_creator'),
        dataset_date=dataset_info.get('dataset_date'),
        task=task
    )
    dataset.save()
    return dataset

def _get_authority_record_status(status):
    statuses = {
        "active": Authority.ACTIVE,
        "inactive": Authority.INACTIVE,
        "duplicate": Authority.DUPLICATE,
        "redirect": Authority.REDIRECT
    }
    return statuses.get(status.lower(), Authority.INACTIVE)

def _get_authority_type(auth_type):
    entity_types = {
        "person": Authority.PERSON,
        "institution": Authority.INSTITUTION,
        "time period": Authority.TIME_PERIOD,
        "geographic term": Authority.GEOGRAPHIC_TERM,
        "serial publication": Authority.SERIAL_PUBLICATION,
        "classification term": Authority.CLASSIFICATION_TERM,
        "concept": Authority.CONCEPT,
        "creative work": Authority.CREATIVE_WORK,
        "event": Authority.EVENT,
        "cross reference": Authority.CROSSREFERENCE,
        "bibliographic list": Authority.BIBLIOGRAPHIC_LIST
    }
    return entity_types.get(auth_type.lower(), "")

def _get_classifcation_system(user, class_system_name):
    classification_systems = cutil.get_classification_systems(user)
    for cs in classification_systems:
        if cs.name == class_system_name:
            print(class_system_name)
            print(cs)
            print(cs.name)
            return cs

def _get_default_classification_system(user, authority_type):
    class_system = ClassificationSystem.objects.filter(default_for__contains=[authority_type])
    if class_system.exists():
        return class_system.first()
    return None

def _create_attribute(type, value):
    attr_type = AttributeType.objects.filter(name=type).first()
    if not attr_type:
        return None
    
    return ImportedAuthority.objects.create(
        attribute_type=attr_type,
        value=str(value),
    )

def _create_linkeddata(data, subject):
    # { "type": "viaf", "value": "https://viaf.org/viaf/12345678" },
    ldtype = LinkedDataType.objects.filter(name=data.get('type')).first()
    ImportedLinkedData.objects.create(
        subject = subject,
        universal_resource_name = data.get("value"),
        type_controlled = ldtype
    )

def _create_ac_relation(data, authority_map, citation, results):
    # data = {
	#	  "authority_id":      null,
	#	  "local_dataset_id":  "DS-001-AUTH-00001",
	#	  "relationship_type": "author",
	#	  "display_name":      "Shapiro, Lisa",
	#	  "order":             1
	#	}
    try:
        existing_authority = None
        new_authority = None
        if data.get('authority_id', None):
            auth_ref = data['authority_id']
            existing_authority = Authority.objects.filter(pk=auth_ref).first()  
        else:
            new_auth_ref = data.get('local_dataset_id', None)
            if new_auth_ref and new_auth_ref in authority_map:
                new_authority = authority_map[new_auth_ref]
            else:
                results.append(('ERROR', 'ACRelation', '', f'Missing authority reference for ACRelation: {data.get("authority_id")} or {data.get("local_dataset_id")}'))
                return None
            
        type_controlled = _get_acrelation_type(data.get('relationship_type'))
        if not type_controlled:
            results.append(('ERROR', 'ACRelation', '', f'Missing or invalid relationship type: {data.get("relationship_type")}'))
            return None
        
        new_ac_rel_data = {
            'citation': citation,
            'type_controlled': type_controlled,
            'name_for_display_in_citation': data.get('display_name') or None,
            'data_display_order': float(data.get('order')) or 1.0
        }

        if existing_authority:
            new_ac_rel_data['existing_authority'] = existing_authority
        elif new_authority:
            new_ac_rel_data['authority'] = new_authority
        else:
            results.append(('ERROR', 'ACRelation', '', f'Could not find authority for ACRelation with references: {data.get("authority_id")} or {data.get("local_dataset_id")}'))
            return None

        print(new_ac_rel_data)
        ac_rel = ImportedACRelation(**new_ac_rel_data)
        ac_rel.save()
        results.append(('SUCCESS', 'ACRelation', ac_rel.pk, 'Created'))
        print("Created ACRelation with id {id}".format(id=ac_rel.pk))
    except Exception as e:
        logging.exception(e)
        results.append(('ERROR', 'ACRelation', '', 'Error creating acrelation: %s' % repr(e)))

def _get_acrelation_type(acr_type):
    roles = {
        "author": ACRelation.AUTHOR,
        "editor": ACRelation.EDITOR,
        "advisor": ACRelation.ADVISOR,
        "contributor": ACRelation.CONTRIBUTOR,
        "translator": ACRelation.TRANSLATOR,
        "subject": ACRelation.SUBJECT,
        "category": ACRelation.CATEGORY,
        "publisher": ACRelation.PUBLISHER,
        "school": ACRelation.SCHOOL,
        "institution": ACRelation.INSTITUTION,
        "meeting": ACRelation.MEETING,
        "periodical": ACRelation.PERIODICAL,
        "book series": ACRelation.BOOK_SERIES,
        "committee member": ACRelation.COMMITTEE_MEMBER,
        "organizer": ACRelation.ORGANIZER,
        "interviewer": ACRelation.INTERVIEWER,
        "guest": ACRelation.GUEST,
        "creator": ACRelation.CREATOR,
        "producer": ACRelation.PRODUCER,
        "director": ACRelation.DIRECTOR,
        "writer": ACRelation.WRITER,
        "performer": ACRelation.PERFORMER,
        "collector": ACRelation.COLLECTOR,
        "archivist": ACRelation.ARCHIVIST,
        "researcher": ACRelation.RESEARCHER,
        "developer": ACRelation.DEVELOPER,
        "compiler": ACRelation.COMPILER,
        "awardee": ACRelation.AWARDEE,
        "officer": ACRelation.OFFICER,
        "host": ACRelation.HOST,
        "distributor": ACRelation.DISTRIBUTOR,
        "archival repository": ACRelation.ARCHIVAL_REPOSITORY,
        "maintaining institution": ACRelation.MAINTAINING_INSTITUTION,
        "presenting group": ACRelation.PRESENTING_GROUP
    }
    return roles.get(acr_type.lower(), "")

def _create_cc_relation(results, cit_map,data):
        try:
            subj = data.get('subject_id') or data.get('subject')
            obj = data.get('object_id') or data.get('object')
            subj_obj = cit_map.get(subj) or ImportedCitation.objects.filter(pk=subj).first()
            obj_obj = cit_map.get(obj) or ImportedCitation.objects.filter(pk=obj).first()
            if not subj_obj or not obj_obj:
                return results.append(('WARNING', 'CCRelation', '', 'Missing citations for ccrelation'))

            ccr = ImportedCCRelation.objects.create(
                subject=subj_obj,
                object=obj_obj,
                name=data.get('name') or '',
                description=data.get('description') or '',
                type_controlled=data.get('type_controlled') or None,
                type_free=data.get('type_free') or None,
                data_display_order=data.get('data_display_order') or 1.0
            )
            ccr.save()
            results.append(('SUCCESS', 'CCRelation', ccr.pk, 'Created'))
        except Exception as e:
            logging.exception(e)
            results.append(('ERROR', 'CCRelation', '', 'Error creating ccrelation: %s' % repr(e)))

def _save_results(path, results, headings):
    with smart_open.smart_open(path, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(headings)
        for result in results:
            writer.writerow(result)