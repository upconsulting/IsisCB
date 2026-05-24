from datetime import datetime

from celery import shared_task
import logging

import smart_open, json, csv

from django.contrib.auth.models import User
from jsonimport.models import (
    ImportedAttribute, ImportedAuthority, ImportedAuthorityStatus, ImportedCitation, ImportedACRelation,
    ImportedCCRelation, ImportedCitationStatus, ImportedDataset, ImportedPartDetails,
    ImportedLinkedData
)

from isisdata.models import (
    AsyncTask, AttributeType, CitationSubtype, ClassificationSystem, 
    Tenant, Authority, Citation, CuratedMixin, ACRelation, CCRelation,
    LinkedDataType
)
from curation import curation_util as cutil


logger = logging.getLogger(__name__)

NEW_RECORD_ACTION = "add new record"

@shared_task
def import_records(authorities_file_path, citations_file_path, error_path, dataset_id, task_id, user_id):
   
    logging.info('Importing JSON records from %s and %s.' % (citations_file_path, authorities_file_path))

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
        with smart_open.smart_open(authorities_file_path, 'r') as f:
            content = f.read()
            authorities_data = json.loads(content)
    except Exception as e:
        logging.exception(e)
        results.append((ERROR, 'file', '', 'Could not read or parse authorities JSON: %s' % repr(e)))
        _save_results(error_path, results, ('Type', 'Title', 'Ids', 'Message'))
        if task:
            task.state = 'ERROR'
            task.save()
        return
    
    try:
        with smart_open.smart_open(citations_file_path, 'r') as f:
            content = f.read()
            citations_data = json.loads(content)    
    except Exception as e:
        logging.exception(e)
        results.append((ERROR, 'file', '', 'Could not read or parse citations JSON: %s' % repr(e)))
        _save_results(error_path, results, ('Type', 'Title', 'Ids', 'Message'))
        if task:
            task.state = 'ERROR'
            task.save()
        return
    
    dataset = ImportedDataset.objects.filter(pk=dataset_id).first()
    dataset.authorities_imported_on = datetime.now()
    dataset.citations_imported_on = datetime.now()

    # let's first check if dataset info in both files are the same
    authorities_dataset_info = authorities_data.get('dataset') or {}
    citations_dataset_info = citations_data.get('dataset') or {}

    if authorities_dataset_info != citations_dataset_info:
        results.append((ERROR, 'Dataset', '', 'Dataset info in authorities and citations files do not match'))
        _save_results(error_path, results, ('Type', 'Title', 'Ids', 'Message'))
        if task:
            task.state = 'ERROR'
            task.save()
        return

    authorities = []
    citations = []

    authority_items = authorities_data.get('records') or []
    citation_items = citations_data.get('records') or []
    
    total = len(authority_items) + len(citation_items)

    if task:
        task.max_value = total
        task.current_value = 0
        task.save()

    # maps from local id to created instance
    auth_map = {}
    citations_by_id = {}

    user = User.objects.filter(username=user_id).first()
    
    # create authorities
    for authority_info in authority_items:
        # we only add new records for now
        if authority_info.get("action") == NEW_RECORD_ACTION:
            _create_imported_authority(user, task, tenant, results, dataset, auth_map, authority_info)
        
    
    # create citations
    for citation_data in citation_items:
        # we only create new records for now
        if citation_data.get("action") == NEW_RECORD_ACTION:
            citation = _create_imported_citation(task, results, dataset, citations_by_id, citation_data)
            if citation:
                for ac_data in citation_data.get('author') or []:
                    _create_ac_relation(ac_data, auth_map, citation, results, type_controlled=ACRelation.AUTHOR)
                for ac_data in citation_data.get('editor') or []:
                    _create_ac_relation(ac_data, auth_map, citation, results, type_controlled=ACRelation.EDITOR)
                for ac_data in citation_data.get('advisor') or []:
                    _create_ac_relation(ac_data, auth_map, citation, results, type_controlled=ACRelation.ADVISOR)
                for ac_data in citation_data.get('school') or []:
                    _create_ac_relation(ac_data, auth_map, citation, results, type_controlled=ACRelation.SCHOOL)
                for ac_data in citation_data.get('publisher') or []:
                    _create_ac_relation(ac_data, auth_map, citation, results, type_controlled=ACRelation.PUBLISHER)
                for ac_data in citation_data.get('subject') or []:
                    _create_ac_relation(ac_data, auth_map, citation, results, type_controlled=ACRelation.SUBJECT)
                for ac_data in citation_data.get('category') or []:
                    _create_ac_relation(ac_data, auth_map, citation, results, type_controlled=ACRelation.CATEGORY)
            else:
                results.append((ERROR, 'Citation', citation_data.get('local_citation_id') or '', 'Failed to create citation, so related authorities could not be linked.'))
            
    # create ccrelations; we first have to have them all before we can link them
    for citation_data in citation_items:
        citation = citations_by_id.get(citation_data.get('local_citation_id'))
        if not citation:
            results.append((ERROR, 'CCRelation', citation_data.get('local_citation_id') or '', 'Failed to find citation for ccrelation with citation local id reference: %s. Ccrelation could not be created.' % citation_data.get('local_citation_id')))
            continue
        for cc_data in citation_data.get('related_citations') or []:
            _create_cc_relation(results, citations_by_id, cc_data, citation)  


    # write results
    _save_results(error_path, results, ('Type', 'Title', 'Ids', 'Message'))

    if task:
        task.state = SUCCESS
        task.save()

def _create_imported_citation(task, results, dataset, cit_map, citation_data):
    try:
        title = citation_data.get('title') or ''
        local_id = citation_data.get('local_citation_id')
        
        type_controlled = _get_citation_type(citation_data.get('citation_type'))
        if not type_controlled:
            _create_imported_citation_status(dataset, ImportedCitationStatus.Status.ERROR, f'Could not create citation: \"{title}\" with local id {local_id}. Missing or invalid citation type: {citation_data.get("citation_type")}', results, None)
            return None

        subtype = None
        create_subtype_warning = False
        subtype_warning_message = ''
        if citation_data.get('subtype_name'):
            subtype = CitationSubtype.objects.filter(name=citation_data.get('subtype_name')).first()
            if not subtype:
                create_subtype_warning = True
                subtype_warning_message = f'Citation subtype {citation_data.get("subtype_name")} not found. Citation will be created without subtype.'
            else:
                if subtype.related_citation_type != type_controlled:
                    create_subtype_warning = True
                    subtype_warning_message = f'Citation subtype {citation_data.get("subtype_name")} is not a subtype of citation type {citation_data.get("type_controlled")}. Citation will be created without subtype.'
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

        if create_subtype_warning:
            _create_imported_citation_status(dataset, ImportedCitationStatus.Status.WARNING, subtype_warning_message, results, cit)

        # part details
        pd = ImportedPartDetails.objects.create(
                volume=citation_data.get('volume', ''),
                volume_free_text=citation_data.get('volume', ''),
                volume_begin=citation_data.get('volume_begin',0),
                volume_end=citation_data.get('volume_end',0),
                issue_free_text=citation_data.get('issue',''),
                issue_begin=citation_data.get('issue_begin',0),
                issue_end=citation_data.get('issue_end',0),
                pages_free_text=citation_data.get('pages',''),
                page_begin=citation_data.get('page_begin',0),
                page_end=citation_data.get('page_end',0),
                extent=citation_data.get('extent',0),
                extent_note=citation_data.get('extent_note',''),
                citation=cit
            )
        
        
        for attr in citation_data.get('attributes') or []:
            _create_citation_attribute(attr.get('type'), attr.get('value'), cit, dataset, results)
            
        cit.save()

        for linked_data in citation_data.get('linked_data') or []:
            _create_linkeddata(linked_data, cit)

        cit_map[local_id] = cit

        _create_imported_citation_status(dataset, ImportedCitationStatus.Status.SUCCESS, f'Created citation {title} with local id {local_id}.', results, cit)
        if task:
            task.current_value = task.current_value + 1
            task.save()

        return cit
    except Exception as e:
        logging.exception(e)
        _create_imported_citation_status(dataset, ImportedCitationStatus.Status.ERROR, f'Error creating citation {title} with local id {local_id}: {repr(e)}', results, None)
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
        local_dataset_id = authority_data.get('local_authority_id') or ''
        
        if not type_controlled:
            _create_imported_authority_status(dataset, ImportedAuthorityStatus.Status.ERROR, f'Could not create authority: {name}. Missing or invalid authority type: {authority_data.get("authority_type")}', results, None)
            return None
        
        if authority_data.get('classification_system_name'):
            class_system =_get_classifcation_system(user, authority_data.get('classification_system_name'))
        else:
            class_system =_get_default_classification_system(user, type_controlled)
            print(f'No classification system specified for authority \"{name}\" with local id {local_dataset_id}. Using default classification system {class_system} for authority type {type_controlled}.')
        if not class_system:
            _create_imported_authority_status(dataset, ImportedAuthorityStatus.Status.ERROR, f'Could not create authority \"{name}\". Invalid classification system specified: {authority_data.get("classification_system_name")}, and no default classification system found for authority type {type_controlled}.', results, None)
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
            _create_authority_attribute(attr.get('type'), attr.get('value'), auth, dataset, results)

        auth.save()

        for linked_data in authority_data.get('linked_data') or []:
            _create_linkeddata(linked_data, auth)

        auth_map[local_dataset_id] = auth

        _create_imported_authority_status(dataset, ImportedAuthorityStatus.Status.SUCCESS, f'Created authority {name} with local id {local_dataset_id}.', results, auth)
    except Exception as e:
        logging.exception(e)
        _create_imported_authority_status(dataset, ImportedAuthorityStatus.Status.ERROR, f'Error creating authority {name} with local id {authority_data.get("local_dataset_id") or ""}: {repr(e)}', results, None)
    if task:
        task.current_value = task.current_value + 1
        task.save()

def _create_imported_authority_status(dataset, status, message, results, authority):
    ImportedAuthorityStatus.objects.create(
        dataset=dataset,
        status=status,
        message=message,
        authority=authority
    )
    results.append((status, 'Authority', message))

def _create_imported_citation_status(dataset, status, message, results, citation):
    ImportedCitationStatus.objects.create(
        dataset=dataset,
        status=status,
        message=message,
        citation=citation
    )
    results.append((status, 'Citation', message))
            

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
    return next((cs for cs in classification_systems if cs.name == class_system_name), None)

def _get_default_classification_system(user, authority_type):
    class_system = ClassificationSystem.objects.filter(default_for__contains=[authority_type])
    return class_system.first() if class_system.exists() else None

def _create_authority_attribute(type, value, authority, dataset, results):
    attr_type = AttributeType.objects.filter(name=type).first()
    if not attr_type:
        _create_imported_authority_status(dataset, ImportedAuthorityStatus.Status.ERROR, f'Invalid attribute type specified: {type}', results, authority)
        return None
    
    return ImportedAttribute.objects.create(
        value_authority=authority,
        attribute_type=attr_type,
        value=str(value),
    )

def _create_citation_attribute(type, value, citation, dataset, results):
    attr_type = AttributeType.objects.filter(name=type).first()
    if not attr_type:
        _create_imported_citation_status(dataset, ImportedCitationStatus.Status.ERROR, f'Invalid attribute type specified: {type}', results, citation)
        return None
    
    return ImportedAttribute.objects.create(
        value_citation=citation,
        attribute_type=attr_type,
        value=str(value),
    )

def _create_linkeddata(data, subject):
    # { "type": "viaf", "value": "https://viaf.org/viaf/12345678" },
    ldtype = LinkedDataType.objects.filter(name=data.get('type').upper()).first()
    if not ldtype:
        if type(subject) == ImportedAuthority:
            _create_imported_authority_status(subject.dataset, ImportedAuthorityStatus.Status.ERROR, f'Could not create linked data for authority {subject.name} with local id {subject.local_dataset_id}. Invalid linked data type specified: {data.get("type")}. Linked data not created.', [], subject)
            return
        elif type(subject) == ImportedCitation:
            _create_imported_citation_status(subject.dataset, ImportedCitationStatus.Status.ERROR, f'Could not create linked data for citation {subject.title} with local id {subject.local_dataset_id}. Invalid linked data type specified: {data.get("type")}. Linked data not created.', [], subject)
            return
    
    ImportedLinkedData.objects.create(
        subject = subject,
        universal_resource_name = data.get("value"),
        type_controlled = ldtype
    )

def _create_ac_relation(data, authority_map, citation, results, type_controlled=None):
    # data = {
	#	  "authority_id":      null,
	#	  "local_authority_id":  "DS-001-AUTH-00001",
	#	  "relationship_type": "author",
	#	  "display_name":      "Shapiro, Lisa",
	#	  "order":             1,
    #     "cba_id":             "CBA000044928
	#	}
    try:
        existing_authority = None
        new_authority = None
        if data.get('cba_id', None):
            auth_ref = data['cba_id']
            existing_authority = Authority.objects.filter(pk=auth_ref).first()  
        else:
            new_auth_ref = data.get('local_authority_id', None)
            if new_auth_ref and new_auth_ref in authority_map:
                new_authority = authority_map[new_auth_ref]
            else:
                _create_imported_citation_status(citation.dataset, ImportedCitationStatus.Status.ERROR, f'Missing authority reference for ACRelation for citation {citation.title} with local id {citation.local_dataset_id}: Missing authority reference for ACRelation: {data.get("cba_id")} or {data.get("local_authority_id")}. ACRelation could not be created.', results, citation)
                return None

        if not type_controlled:  
            type_controlled = _get_acrelation_type(data.get('relationship_type'))
        if not type_controlled:
            _create_imported_citation_status(citation.dataset, ImportedCitationStatus.Status.ERROR, f'Missing or invalid relationship type for ACRelation for citation {citation.title} with local id {citation.local_dataset_id}: {data.get("relationship_type")}. ACRelation could not be created.', results, citation)
            return None
        
        new_ac_rel_data = {
            'citation': citation,
            'type_controlled': type_controlled,
            'name_for_display_in_citation': data.get('display_name') or None,
            'data_display_order': float(data.get('order', 1) or 1.0)
        }

        if existing_authority:
            new_ac_rel_data['existing_authority'] = existing_authority
        elif new_authority:
            new_ac_rel_data['authority'] = new_authority
        else:
            _create_imported_citation_status(citation.dataset, ImportedCitationStatus.Status.ERROR, f'Could not find authority for ACRelation with references: {data.get("cba_id")} or {data.get("local_authority_id")}', results, citation)
            return None

        ac_rel = ImportedACRelation(**new_ac_rel_data)
        ac_rel.save()
        results.append(('SUCCESS', 'ACRelation', ac_rel.pk, 'Created'))
        print("Created ACRelation with id {id}".format(id=ac_rel.pk))
    except Exception as e:
        logging.exception(e)
        _create_imported_citation_status(citation.dataset, ImportedCitationStatus.Status.ERROR, f'Error creating ACRelation for citation {citation.title} with local id {citation.local_dataset_id}: {repr(e)}', results, citation) 

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

def _create_cc_relation(results, citations_by_id, data, citation):
        """ 
        {
	  		"citation_id": null,
	   		"local_citation_id": "DS-001-CIT-00043",
	  		"relationship_type": "includes chapter",
	  		"related_citation_role": "subject"
	  	}
        """
        try:
            related_citation_id = None
            related_citation = None
            existing_related_citation = None
            if data.get('cbb_id'):
                related_citation_id = data['cbb_id']
                if not related_citation_id:
                    return results.append(('ERROR', 'CCRelation', '', 'Missing citation reference for CCRelation: no cbb_id or local_citation_id provided'))

                existing_related_citation = Citation.objects.filter(pk=related_citation_id).first()  # verify that citation exists
            
            else:
                related_citation_id = data.get('local_citation_id', None)
                if not related_citation_id:
                    return results.append(('ERROR', 'CCRelation', '', 'Missing citation reference for CCRelation: no cbb_id or local_citation_id provided'))

                related_citation = citations_by_id.get(related_citation_id)
                if not related_citation:
                    return results.append(('ERROR', 'CCRelation', '', f'Could not find citation for CCRelation with local_citation_id reference: {related_citation_id}'))    
            
            subject = None
            object = None
            existing_object = None
            existing_subject = None
            if data.get('related_citation_role') == "object":
                object = related_citation
                existing_object = existing_related_citation
                subject = citation
            elif data.get('related_citation_role') == "subject":
                subject = related_citation
                existing_subject = existing_related_citation
                object = citation
            else:
                return results.append(('ERROR', 'CCRelation', '', f'Missing or invalid related_citation_role for CCRelation: {data.get("related_citation_role")}'))
            
            type_controlled = _get_ccrelation_type(data.get('relationship_type'))  # validate relationship type
            if not type_controlled:
                return results.append(('ERROR', 'CCRelation', '', f'Missing or invalid relationship type for CCRelation: {data.get("relationship_type")}'))
            
            ccr = ImportedCCRelation.objects.create(
                subject=subject,
                existing_subject=existing_subject,
                object=object,
                existing_object=existing_object,
                type_controlled=type_controlled
            )
            ccr.save()
            return results.append(('SUCCESS', 'CCRelation', ccr.pk, 'Created'))
        except Exception as e:
            logging.exception(e)
            return results.append(('ERROR', 'CCRelation', '', 'Error creating ccrelation: %s' % repr(e)))

def _get_ccrelation_type(ccr_type):
    types = {
        "includes chapter": CCRelation.INCLUDES_CHAPTER,
        "includes series article": CCRelation.INCLUDES_SERIES_ARTICLE,
        "includes citation object": CCRelation.INCLUDES_CITATION_OBJECT,
        "review of": CCRelation.REVIEW_OF,
        "reviewed by": CCRelation.REVIEWED_BY,
        "responds to": CCRelation.RESPONDS_TO,
        "associated with": CCRelation.ASSOCIATED_WITH
    }
    return types.get(ccr_type.lower(), "")

def _save_results(path, results, headings):
    with smart_open.smart_open(path, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(headings)
        for result in results:
            writer.writerow(result)