from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import user_passes_test
from django.conf import settings
from django.core.paginator import Paginator

import smart_open, tempfile, os, datetime
import logging

from jsonimport.forms import UploadJsonDataForm
from jsonimport.tasks import import_records
from jsonimport.models import ImportedDataset, ImportedAuthority, ImportedCitation, ImportedAuthorityStatus

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
        'authority_import_status_error': ImportedAuthorityStatus.objects.filter(dataset=dataset, status=ImportedAuthorityStatus.Status.ERROR),
    }

    template = 'jsonimport/view_imported_dataset.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def upload_file(request):
    if request.method == "POST":
        form = UploadJsonDataForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']

            # store file in s3 so we can download when it's being processed
            _datestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            _out_name = '%s--%s' % (_datestamp, uploaded_file.name)
            s3_path = settings.UPLOAD_BULK_CHANGE_PATH + _out_name

            _results_name = '%s--%s' % (_datestamp, 'bulk_import_results.csv')
            s3_error_path = settings.BULK_CHANGE_ERROR_PATH + _results_name

            tempFile, path = tempfile.mkstemp()
            try:
                # we'll write the file first to disk so we can then open it with
                # the correct encoding
                with open(path, 'wb+') as tmp:
                    for chunk in uploaded_file.chunks():
                        tmp.write(chunk)

                # 'utf-8-sig' will open bom or no bom files
                with open(path, 'r', encoding='utf-8-sig') as tmp:
                    with smart_open.smart_open(s3_path, 'w') as f:
                        for line in tmp:
                            f.write(line)
            finally:
                os.remove(path)

            task = AsyncTask.objects.create()
            task.value = _results_name
            task.created_by = request.user
            task.task_type = AsyncTask.ASYNC_TASK_TYPE
            task.state = 'PENDING'
            task.save()

            import_records.delay(s3_path, s3_error_path, task.pk, request.user.id)
            
            return redirect('curation:list_import_tasks')
    else:
        form = UploadJsonDataForm()

    return render(request, "jsonimport/import_json.html", {"form": form})