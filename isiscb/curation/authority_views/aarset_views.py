from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, QueryDict #, HttpResponseForbidden, Http404, , JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required, user_passes_test

from rules.contrib.views import permission_required, objectgetter

from isisdata.models import *
from curation.forms import *

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def aarsets(request):

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'aarsets',
    }

    template = 'curation/aarelationsets.html'
    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def change_aarset(request):
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'aarsets',
    }

    if request.method == "GET":
        template = 'curation/aarelationset_change.html'
        context = {
            'form': AARSetForm(prefix='aarset')
        }
        return render(request, template, context)
