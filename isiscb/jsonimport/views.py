from django.shortcuts import render
from django.contrib.admin.views.decorators import user_passes_test
from django.conf import settings

import smart_open, tempfile, os, datetime
import logging

from jsonimport.forms import UploadJsonDataForm
from jsonimport.tasks import import_records

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
            task.save()

            import_records.delay(s3_path, s3_error_path, task.pk, request.user.id)
            
            return render(request, "jsonimport/import_json.html", {
                "filename": "filename"
            })
    else:
        form = UploadJsonDataForm()

    return render(request, "jsonimport/import_json.html", {"form": form})