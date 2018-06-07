from django.contrib.admin.views.decorators import staff_member_required, user_passes_test
from django.http import HttpResponseRedirect

from django.shortcuts import get_object_or_404, render, redirect
from django.core.urlresolvers import reverse

from django.utils.http import urlencode

from isisdata.models import *
from isisdata import tasks as data_tasks

from curation.forms import *

from curation.taskslib import authority_tasks

import smart_open

ACTION_DICT = {
    BulkChangeCSVForm.CREATE_ATTR: 'add_attributes_to_authority',
    BulkChangeCSVForm.UPDATE_ATTR: 'update_elements'
}

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def bulk_changes(request):


    tasks = AsyncTask.objects.filter(created_on__isnull=False).order_by('-created_on')[:20]
    context = {
        'curation_section': 'bulk',
        'tasks': tasks,
    }

    template = 'curation/bulk/bulk_changes.html'
    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def bulk_change_from_csv(request):
    context = {
        'curation_section': 'bulk',
    }

    if request.method == 'GET':
        context.update({
            'form': BulkChangeCSVForm()
        })
        template = 'curation/bulk/show_bulk_change_from_csv.html'
    elif request.method == 'POST':
        form = BulkChangeCSVForm(request.POST, request.FILES)
        if form.is_valid():
            bulk_method = getattr(authority_tasks,ACTION_DICT[form.cleaned_data['action']])
            uploaded_file = form.cleaned_data['csvFile']
            # store file in s3 so we can download when it's being processed
            _datestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            _out_name = '%s--%s' % (_datestamp, uploaded_file.name)
            s3_path = 's3://%s:%s@%s/%s' % (settings.AWS_ACCESS_KEY_ID,
                                            settings.AWS_SECRET_ACCESS_KEY,
                                            settings.AWS_EXPORT_BUCKET_NAME,
                                            _out_name)

            _results_name = '%s--%s' % (_datestamp, 'results.csv')
            s3_error_path = 's3://%s:%s@%s/%s' % (settings.AWS_ACCESS_KEY_ID,
                                            settings.AWS_SECRET_ACCESS_KEY,
                                            settings.AWS_EXPORT_BUCKET_NAME,
                                            _results_name)

            with smart_open.smart_open(s3_path, 'wb') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

            task = AsyncTask.objects.create()
            task.value = _results_name
            task.created_by = request.user
            task.save()

            bulk_method.delay(s3_path, s3_error_path, task.id)

            target = reverse('curation:bulk-csv-status') \
                     + '?' + urlencode({'task_id': task.id})
            return HttpResponseRedirect(target)

        context.update({
            'form': form
        })
        template = 'curation/bulk/show_bulk_change_from_csv.html'

    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def bulk_csv_status(request):
    template = 'curation/export_status.html'
    context = {
        'exported_type': 'BULK_CHANGES'
    }
    # target = request.GET.get('target')
    task_id = request.GET.get('task_id')
    task = AsyncTask.objects.get(pk=task_id)
    target = task.value

    download_target = 'https://%s.s3.amazonaws.com/%s' % (settings.AWS_EXPORT_BUCKET_NAME, target)
    context.update({'download_target': download_target, 'task': task})
    return render(request, template, context)
