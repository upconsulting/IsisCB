from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.admin.views.decorators import user_passes_test
from django.conf import settings
from django.core.paginator import Paginator

import smart_open, tempfile, os, datetime
import logging

from jsonimport.forms import UploadJsonDataForm
from jsonimport.tasks import import_records
from jsonimport.models import ImportedACRelation, ImportedCCRelation, ImportedDataset, ImportedAuthority, ImportedCitation, ImportedAuthorityStatus, ImportedCitationStatus, ImportedPartDetails

from curation import curation_util as cutil

from isisdata.models import AsyncTask

logger = logging.getLogger(__name__)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def import_json(request):
    
    context = {
        'curation_section': 'import',
    }

    template = 'jsonimport/import_json.html'
    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def create_imported_dataset(request):
    if request.method == "POST":
        tenant = cutil.get_tenant(request.user)
        dataset = ImportedDataset.objects.create(created_by=request.user, name=request.POST.get('ds-name'), owning_tenant=tenant)

        return redirect('curation:view_imported_dataset', dataset_id=dataset.pk)
    else:
        context = {
            'curation_section': 'import',
        }

        template = 'jsonimport/create_new_dataset.html'
        return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def list_imported_datasets(request):
    tenant = cutil.get_tenant(request.user)
    datasets = ImportedDataset.objects.filter(owning_tenant=tenant).order_by('-created_on')

    context = {
        'curation_section': 'import',
        'datasets': datasets
    }

    template = 'jsonimport/list_imported_datasets.html'
    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def view_imported_dataset(request, dataset_id):
    if request.method == "POST":
        form = UploadJsonDataForm(request.POST, request.FILES)
        if form.is_valid():
            dataset = get_object_or_404(ImportedDataset, pk=dataset_id)
            
            # we need to delete previous data
            for authority in ImportedAuthority.objects.filter(dataset=dataset_id):
                authority.linkeddata_entries.all().delete()
                for attr in authority.get_attributes():
                    attr.delete()

            for citation in ImportedCitation.objects.filter(dataset=dataset_id):
                citation.linkeddata_entries.all().delete()
                for attr in citation.get_attributes():
                    attr.delete()

            ImportedAuthority.objects.filter(dataset=dataset).delete()
            ImportedCitation.objects.filter(dataset=dataset).delete()
            ImportedAuthorityStatus.objects.filter(dataset=dataset).delete()
            ImportedCitationStatus.objects.filter(dataset=dataset).delete()

            if dataset.task:
                dataset.task.delete()
            
            citations_file = request.FILES['citations_file']
            authorities_file = request.FILES['authorities_file']
            _process_files(citations_file, authorities_file, dataset, request.user)

        return redirect('curation:view_imported_dataset', dataset_id=dataset.pk)
    
    # otherwise, show details about the dataset and the authorities/citations that were imported as part of it
    tenant = cutil.get_tenant(request.user)
    dataset = ImportedDataset.objects.filter(pk=dataset_id, owning_tenant=tenant).first()
    authorities = ImportedAuthority.objects.filter(dataset=dataset)
    citations = ImportedCitation.objects.filter(dataset=dataset)

    citation_paginator = Paginator(citations, 25)
    page_number = request.GET.get('page')
    citations_page = citation_paginator.get_page(page_number)
    total_citations = citations.count()
    
    authority_paginator = Paginator(authorities, 25)
    page_number = request.GET.get('page')
    authorities_page = authority_paginator.get_page(page_number)
    total_authorities = authorities.count()

    context = {
        'curation_section': 'import',
        'dataset': dataset,
        'authorities': authorities_page,
        'citations': citations_page,
        'total_citations': total_citations,
        'total_authorities': total_authorities,
        'authority_import_status_success_count': ImportedAuthorityStatus.objects.filter(dataset=dataset, status=ImportedAuthorityStatus.Status.SUCCESS).count(),
        'authority_import_status_error': ImportedAuthorityStatus.objects.filter(dataset=dataset, status=ImportedAuthorityStatus.Status.ERROR, authority__isnull=False),
        'citation_import_status_success_count': ImportedCitationStatus.objects.filter(dataset=dataset, status=ImportedCitationStatus.Status.SUCCESS).count(),
        'citation_import_status_error': ImportedCitationStatus.objects.filter(dataset=dataset, status=ImportedCitationStatus.Status.ERROR, citation__isnull=False),
        'failed_citation_imports': ImportedCitationStatus.objects.filter(dataset=dataset, status=ImportedCitationStatus.Status.ERROR, citation__isnull=True),
        'failed_authority_imports': ImportedAuthorityStatus.objects.filter(dataset=dataset, status=ImportedAuthorityStatus.Status.ERROR, authority__isnull=True)
    }

    template = 'jsonimport/view_imported_dataset.html'
    return render(request, template, context)


def _process_files(citations_file, authorities_file, dataset, user):
    # store file in s3 so we can download when it's being processed
    _datestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _citations_file_name = '%s--%s' % (_datestamp, citations_file.name)
    citations_s3_path = settings.UPLOAD_BULK_CHANGE_PATH + _citations_file_name
    _authorities_file_name = '%s--%s' % (_datestamp, authorities_file.name)
    authorities_s3_path = settings.UPLOAD_BULK_CHANGE_PATH + _authorities_file_name

    _results_name = '%s--%s' % (_datestamp, 'import_results.csv')
    s3_error_path = settings.BULK_CHANGE_ERROR_PATH + _results_name

    try:
        with smart_open.smart_open(citations_s3_path, 'wb') as f:
            for line in citations_file:
                f.write(line)
    except Exception as e:
        logger.error("There was an unexpected error uploading the authorities file.", e)
    
    try:   
        with smart_open.smart_open(authorities_s3_path, 'wb') as f:
            for line in authorities_file:
                f.write(line)
    except Exception as e:
        logger.error("There was an unexpected error uploading the authorities file.", e)

    task = AsyncTask.objects.create()
    task.value = dataset.name
    task.created_by = user
    task.task_type = AsyncTask.ASYNC_TASK_TYPE
    task.state = 'PENDING'
    task.save()

    dataset.task = task
    dataset.save()

    logger.error("Authorities file: %s, Citations file: %s" % (authorities_s3_path, citations_s3_path))
    import_records.delay(authorities_s3_path, citations_s3_path, s3_error_path, dataset.id, task.pk, user.id)
    