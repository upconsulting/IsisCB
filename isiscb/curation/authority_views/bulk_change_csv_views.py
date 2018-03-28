from django.contrib.admin.views.decorators import staff_member_required, user_passes_test
from django.http import HttpResponseRedirect

from django.shortcuts import get_object_or_404, render, redirect
from django.core.urlresolvers import reverse

from isisdata.models import *
from isisdata import tasks as data_tasks

from curation.forms import *

from curation.taskslib import authority_tasks

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
            task = AsyncTask.objects.create()
            authority_tasks.add_attributes_to_authority(form.cleaned_data['csvFile'], task.id)
            return HttpResponseRedirect(reverse('curation:authority_list'))
        context.update({
            'form': form
        })
        template = 'curation/authority/show_bulk_change_from_csv.html'

    return render(request, template, context)
