from django.contrib.admin.views.decorators import staff_member_required, user_passes_test
from django.http import HttpResponseRedirect

from django.shortcuts import get_object_or_404, render, redirect
from django.core.urlresolvers import reverse

from django.utils.http import urlencode

from isisdata.models import *
from isisdata import tasks as data_tasks

from curation.forms import *

from curation.taskslib import authority_tasks, creation_tasks

import smart_open
import operator

ACTION_DICT = {
    BulkChangeCSVForm.CREATE_ATTR: (authority_tasks, 'add_attributes_to_authority'),
    BulkChangeCSVForm.UPDATE_ATTR: (authority_tasks, 'update_elements'),
    BulkChangeCSVForm.CREATE_LINKED_DATA: (creation_tasks, 'create_records', 'linkeddata'),
    BulkChangeCSVForm.CREATE_ACRELATIONS: (creation_tasks, 'create_records', 'acrelation'),
    BulkChangeCSVForm.CREATE_CCRELATIONS: (creation_tasks, 'create_records', 'ccrelation'),
    BulkChangeCSVForm.CREATE_AUTHORITIES: (creation_tasks, 'create_records', 'authority'),
    BulkChangeCSVForm.CREATE_CITATIONS: (creation_tasks, 'create_records', 'citation'),
    BulkChangeCSVForm.MERGE_AUTHORITIES: (authority_tasks, 'merge_authorities'),
}

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def timeline_tasks(request):
    if request.GET.get('find_authority', None):
        timelines = CachedTimeline.objects.filter(authority_id=request.GET.get('find_authority', None))[:50]
    else:
        timelines = CachedTimeline.objects.order_by('-created_at')[:50]

    authority_ids = [timeline.authority_id for timeline in timelines]
    authorities = Authority.objects.filter(id__in=authority_ids).values('id', 'name')
    authority_names = {authority['id'] : authority['name'] for authority in authorities}
    context = {
        'curation_section': 'bulk',
        'timelines': timelines,
        'authority_names': authority_names,
    }
    template = 'curation/bulk/timelines.html'
    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def timeline_delete(request, authority_id):
    if (request.method == 'POST'):
        cached_timeline = CachedTimeline.objects.filter(authority_id=authority_id).order_by('-created_at').first()
        if cached_timeline:
            cached_timeline.recalculate = True
            cached_timeline.save()

    return HttpResponseRedirect(reverse('curation:timeline_tasks',))

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
            bulk_method = getattr(ACTION_DICT[form.cleaned_data['action']][0], ACTION_DICT[form.cleaned_data['action']][1])
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

            # this is ugly but the easiest for now
            if ACTION_DICT[form.cleaned_data['action']][1] == 'create_records':
                bulk_method.delay(s3_path, s3_error_path, task.id, request.user.id, ACTION_DICT[form.cleaned_data['action']][2])
            else:
                bulk_method.delay(s3_path, s3_error_path, task.id, request.user.id)

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
