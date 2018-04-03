from django.contrib.admin.views.decorators import staff_member_required, user_passes_test
from django.http import HttpResponseRedirect

from django.shortcuts import get_object_or_404, render, redirect
from django.core.urlresolvers import reverse

from isisdata.models import *
from isisdata import tasks as data_tasks

from curation.forms import *

from curation.taskslib import authority_tasks

import smart_open

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def bulk_change_from_csv(request):
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
    }

    if request.method == 'GET':
        context.update({
            'form': BulkChangeCSVForm()
        })
        template = 'curation/authority/show_bulk_change_from_csv.html'
    elif request.method == 'POST':
        form = BulkChangeCSVForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['csvFile']
            # store file in s3 so we can download when it's being processed
            _datestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            _out_name = '%s--%s' % (_datestamp, uploaded_file.name)
            #s3_path = 's3://%s:%s@%s/%s' % (settings.AWS_ACCESS_KEY_ID,
            #                                settings.AWS_SECRET_ACCESS_KEY,
            #                                settings.AWS_EXPORT_BUCKET_NAME,
            #                                _out_name)
            s3_path = '/Users/jdamerow/Up/Isis/ISISCB-1021/uploads/' + _out_name

            with smart_open.smart_open(s3_path, 'wb') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

            task = AsyncTask.objects.create()
            authority_tasks.add_attributes_to_authority.delay(s3_path, task.id)
            return HttpResponseRedirect(reverse('curation:authority_list'))
        context.update({
            'form': form
        })
        template = 'curation/authority/show_bulk_change_from_csv.html'

    return render(request, template, context)
