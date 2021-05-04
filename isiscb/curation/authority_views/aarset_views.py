from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, QueryDict #, HttpResponseForbidden, Http404, , JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required, user_passes_test
from django.core.paginator import Paginator

from rules.contrib.views import permission_required, objectgetter

from isisdata.models import *
from curation.forms import *

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def aarsets(request):

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'aarsets',
    }

    aarsets = AARSet.objects.all()
    paginator = Paginator(aarsets, 25)

    page_nr = request.GET.get('page', 1)
    page = paginator.page(page_nr)

    context.update({
        'sets': page.object_list,
        'page_nr': page_nr,
        'page_count': paginator.num_pages
    })

    template = 'curation/aarelationsets.html'
    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def change_aarset(request, aarset_id=None):
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'aarsets',
    }

    aarset = None
    if aarset_id:
        aarset = AARSet.objects.filter(pk=aarset_id).first()

    if request.method == "POST":
        form = AARSetForm(request.POST, prefix='aarset', instance=aarset)
        if form.is_valid():
            form.save()

            target = reverse('curation:aarsets')
            return HttpResponseRedirect(target)


    context = {
        'form': AARSetForm(prefix='aarset', instance=aarset),
        'instance': aarset,
    }
    template = 'curation/aarelationset_change.html'
    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def delete_aarset(request, aarset_id):
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'aarsets',
    }

    aarset = None
    if aarset_id:
        aarset = AARSet.objects.filter(pk=aarset_id).first()

    msgs = {
        'type': '',
        'msg': ''
    }
    if not aarset:
        msgs.update({
            'type': "error",
            'msg': 'AARSet with ID does not exist.'
        })

    if request.method == "POST":
        aarset.delete()
        msgs.update({
            'type': "success",
            'msg': 'AARSet successfully deleted.'
        })

    target = reverse('curation:aarsets') + '?type=' + msgs['type'] + "&msg=" + msgs['msg']
    return HttpResponseRedirect(target)
