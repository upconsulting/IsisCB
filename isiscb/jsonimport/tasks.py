from celery import shared_task
import logging

import smart_open, json, csv

from django.contrib.auth.models import User
from jsonimport.models import (
    ImportedAuthority, ImportedCitation, ImportedACRelation,
    ImportedCCRelation, ImportedDataset, ImportedPartDetails
)
from dateutil.parser import parse as parse_date

from isisdata.models import AsyncTask, AttributeType, CitationSubtype, ClassificationSystem, Tenant, Authority, Citation, CuratedMixin, Person
from curation import utils as cutil


logger = logging.getLogger(__name__)

@shared_task
def import_records(file_path, error_path, task_id, user_id, tenant_id):
   
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
        
    tenant = Tenant.objects.filter(pk=tenant_id).first()
    if not tenant:
        logging.exception('Could not find Tenant with id %s' % tenant_id)
        return

    results = []

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
    
    dataset = _create_dataset(user_id, tenant, data.get('dataset_info') or {})

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
    for a in authorities:
        _create_imported_authority(user, task, tenant, results, dataset, auth_map, a)
        # TODO: create attrivbutes
        # TODO: create linked data
        # TODO: existing citations


    # create citations
    for c in citations:
        _create_imported_citation(SUCCESS, ERROR, task, tenant, results, cit_map, c)
        # TODO: create attrivbutes
        # TODO: create linked data
        # TODO: existing authorities


    # second pass: relations
    # AC relations can be provided on citations under 'related_authorities' or on authorities under 'related_citations'
    def _create_ac_relation(data):
        try:
            # try citation-centric relation
            cit_ref = data.get('citation_id') or data.get('citation') or data.get('subject')
            auth_ref = data.get('authority_id') or data.get('authority') or data.get('object')

            cit_obj = None
            auth_obj = None
            if cit_ref in cit_map:
                cit_obj = cit_map[cit_ref]
            elif isinstance(cit_ref, (int, str)):
                cit_obj = ImportedCitation.objects.filter(pk=cit_ref).first()

            if auth_ref in auth_map:
                auth_obj = auth_map[auth_ref]
            elif isinstance(auth_ref, (int, str)):
                auth_obj = ImportedAuthority.objects.filter(pk=auth_ref).first()

            if not cit_obj or not auth_obj:
                return results.append((WARNING, 'ACRelation', '', 'Missing citation or authority for relation'))

            acr = ImportedACRelation.objects.create(
                citation=cit_obj,
                authority=auth_obj,
                name=data.get('name') or '',
                description=data.get('description') or '',
                type_controlled=data.get('type_controlled') or data.get('type') or None,
                type_free=data.get('type_free') or None,
                name_for_display_in_citation=data.get('name_for_display_in_citation') or None,
                name_as_entered=data.get('name_as_entered') or None,
                personal_name_first=data.get('personal_name_first') or None,
                personal_name_last=data.get('personal_name_last') or None,
                personal_name_suffix=data.get('personal_name_suffix') or None,
                data_display_order=data.get('data_display_order') or 1.0
            )
            acr.save()
            results.append((SUCCESS, 'ACRelation', acr.pk, 'Created'))
        except Exception as e:
            logging.exception(e)
            results.append((ERROR, 'ACRelation', '', 'Error creating acrelation: %s' % repr(e)))

    def _create_cc_relation(data):
        try:
            subj = data.get('subject_id') or data.get('subject')
            obj = data.get('object_id') or data.get('object')
            subj_obj = cit_map.get(subj) or ImportedCitation.objects.filter(pk=subj).first()
            obj_obj = cit_map.get(obj) or ImportedCitation.objects.filter(pk=obj).first()
            if not subj_obj or not obj_obj:
                return results.append((WARNING, 'CCRelation', '', 'Missing citations for ccrelation'))

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
            results.append((SUCCESS, 'CCRelation', ccr.pk, 'Created'))
        except Exception as e:
            logging.exception(e)
            results.append((ERROR, 'CCRelation', '', 'Error creating ccrelation: %s' % repr(e)))

    # scan original input for relation definitions
    def _scan_and_create_relations(items):
        for item in items:
            # citation may have related_authorities
            if isinstance(item, dict):
                if 'related_authorities' in item and item['related_authorities']:
                    for r in item['related_authorities']:
                        # r can be id or dict
                        if isinstance(r, dict):
                            _create_ac_relation(dict(r, citation_id=_get_input_id(item)))
                        else:
                            _create_ac_relation({'citation_id': _get_input_id(item), 'authority_id': r})

                if 'related_citations' in item and item['related_citations']:
                    for r in item['related_citations']:
                        if isinstance(r, dict):
                            _create_cc_relation(dict(r, subject_id=_get_input_id(item)))
                        else:
                            _create_cc_relation({'subject_id': _get_input_id(item), 'object_id': r})

    try:
        _scan_and_create_relations(citations)
        _scan_and_create_relations(authorities)
    except Exception:
        logging.exception('Error creating relations')

    # write results
    _save_results(error_path, results, ('Type', 'Title', 'Ids', 'Message'))

    if task:
        task.state = 'SUCCESS'
        task.save()

def _create_imported_citation(user, task, tenant, results, cit_map, c):
    try:
        title = c.get('title') or ''
        local_id = c.get('local_dataset_id')
        
        type_controlled = _get_citation_type(c.get('type_controlled'))
        if not type_controlled:
            results.append(('ERROR', 'Citation', local_id, f'Missing or invalid citation type: {c.get("type_controlled")}'))
            return None

        subtype = None
        if c.get('subtype_name'):
            subtype = CitationSubtype.objects.filter(name=c.get('subtype_name')).first()
            if not subtype:
                results.append(('WARNING', 'Citation', local_id, f'Invalid citation subtype: {c.get("subtype_name")}'))
            else:
                if subtype.related_citation_type != type_controlled:
                    results.append(('WARNING', 'Citation', local_id, f'Citation subtype {c.get("subtype_name")} is not a subtype of citation type {c.get("type_controlled")}'))  
                    subtype = None      
            
        cit = ImportedCitation.objects.create(
            dataset_id=local_id,
            title=title,
            complete_citation=c.get('full_citation') or '',
            subtype=subtype,
            description=c.get('description') or '',
            type_controlled=type_controlled,
            abstract=c.get('abstract') or '',
            edition_details=c.get('edition_details') or '',
            physical_details=c.get('physical_details') or '',
            owning_tenant=tenant
        )

        # part details
        part = c.get('part_details') or None
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
        
        for attr in c.get('attributes') or []:
            attribute = _create_attribute(attr.get('type'), attr.get('value'))
            if attribute:
                cit.attributes.add(attribute)

        cit.save()

        # TODO add inked data

        cit_map[local_id] = cit

        results.append(('SUCCESS', 'Citation', f"{local_id}: {title}", 'Created'))
    except Exception as e:
        logging.exception(e)
        results.append(('ERROR', 'Citation', c.get('id') or '', 'Error creating citation: %s' % repr(e)))
    if task:
        task.current_value = task.current_value + 1
        task.save()

def _get_citation_type(cit_type):
    resource_types = {
        "Book": "BO",
        "Article": "AR",
        "Chapter": "CH",
        "Review": "RE",
        "Essay Review": "ES",
        "Thesis": "TH",
        "Event": "EV",
        "Web Object": "WO",
        "Multimedia Object": "MO",
        "Archive Object": "AO",
        "Digital Resource": "DR",
        "Personal Recognition": "PC",
        "Presentation": "PR",
        "Interactive": "IN",
        "Website": "WE",
        "Application": "AP"
    }
    return dict(Citation.TYPE_CHOICES).get(resource_types.get(cit_type, "")) or None

def _create_imported_authority(user, task, tenant, results, dataset, auth_map, a):
    try:
        name = a.get('name', '')
        type_controlled = _get_authority_type(a.get('type_controlled'))
        local_dataset_id = a.get('local_dataset_id') or ''
        
        if not type_controlled:
            results.append(('ERROR', 'Authority', local_dataset_id, f'Missing or invalid authority type: {a.get("type_controlled")}'))
            return None
        
        if a.get('classification_system_name'):
            class_system =_get_classifcation_system(user, a.get('classification_system_name'))
        else:
            class_system =_get_default_classification_system(user, type_controlled)
        if not class_system:
            results.append(('ERROR', 'Authority', local_dataset_id, f'Invalid classification system or no default classification system: {a.get("classification_system_name")}'))
            return None
        
        auth = ImportedAuthority.objects.create(
                name=name,
                dataset_id=local_dataset_id,
                dataset=dataset,
                description=a.get('description') or '',
                type_controlled=type_controlled,
                classification_system=class_system,
                classification_code=a.get('classification_code') or '',
                record_status=a.get('record_status', CuratedMixin.INACTIVE),
                owning_tenant=tenant,
                personal_name_last=a.get('personal_name_last') or '',
                personal_name_first=a.get('personal_name_first') or '',
                personal_name_suffix=a.get('personal_name_suffix') or '',
                personal_name_preferred=a.get('personal_name_preferred') or '',
            )

        for attr in a.get('attributes') or []:
            attribute = _create_attribute(attr.get('type'), attr.get('value'))
            if attribute:
                auth.attributes.add(attribute)

        auth.save()
        auth_map[local_dataset_id] = auth

        results.append(('SUCCESS', 'Authority', local_dataset_id or '', 'Created'))
    except Exception as e:
        logging.exception(e)
        results.append(('ERROR', 'Authority', a.get('local_dataset_id') or '', 'Error creating authority: %s' % repr(e)))
    if task:
        task.current_value = task.current_value + 1
        task.save()

def _create_dataset(user_id, tenant, dataset_info):
    user = User.objects.filter(pk=user_id).first()
    dataset = ImportedDataset.objects.create(
        name=dataset_info.get('dataset_name'),
        owning_tenant=tenant,
        created_by=user,
        description=dataset_info.get('dataset_description'),
        dataset_id=dataset_info.get('dataset_id'),
        dataset_creator=dataset_info.get('dataset_creator'),
        dataset_date=dataset_info.get('dataset_date')
    )
    dataset.save()
    return dataset

def _get_authority_type(auth_type):
    entity_types = {
        "Person": "PE",
        "Institution": "IN",
        "Time Period": "TI",
        "Geographic Term": "GE",
        "Serial Publication": "SE",
        "Classification Term": "CT",
        "Concept": "CO",
        "Creative Work": "CW",
        "Event": "EV",
        "Cross Reference": "CR",
        "Bibliographic List": "BL"
    }
    return dict(Authority.TYPE_CHOICES).get(entity_types.get(auth_type, "")) or None

def _get_classifcation_system(user, class_system_name):
    classification_systems = cutil.get_classification_systems(user)
    for cs in classification_systems:
        if cs.name == class_system_name:
            return cs

def _get_default_classification_system(user, authority_type):
    class_system = ClassificationSystem.objects.filter(default_for__contains=authority_type);
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


def _save_results(path, results, headings):
    with smart_open.smart_open(path, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(headings)
        for result in results:
            writer.writerow(result)