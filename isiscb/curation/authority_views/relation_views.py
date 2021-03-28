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
from isisdata.utils import strip_punctuation, normalize
from isisdata import operations
from isisdata.filters import *
from isisdata import tasks as data_tasks
from curation import p3_port_utils
from curation.forms import *

from curation.contrib.views import check_rules


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def create_acrelation_for_authority(request, authority_id):
    authority = get_object_or_404(Authority, pk=authority_id)
    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'search_key': search_key,
        'current_index': current_index

    }
    if request.method == 'GET':
        initial = {
            'authority': authority.id,
            'name_for_display_in_citation': authority.name
        }
        type_controlled = request.GET.get('type_controlled', None)
        if type_controlled:
            initial.update({'type_controlled': type_controlled.upper()})
        form = ACRelationForm(prefix='acrelation', initial=initial)

    elif request.method == 'POST':
        form = ACRelationForm(request.POST, prefix='acrelation')
        if form.is_valid():
            form.save()

            target = reverse('curation:curate_authority', args=(authority.id,)) + '?tab=acrelations'
            if search_key and current_index:
                target += '&search=%s&current=%s' % (search_key, current_index)
            return HttpResponseRedirect(target)

    context.update({
        'form': form,
    })
    template = 'curation/authority_acrelation_changeview.html'
    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def create_aarelation_for_authority(request, authority_id):
    authority = get_object_or_404(Authority, pk=authority_id)
    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'search_key': search_key,
        'current_index': current_index

    }
    if request.method == 'GET':
        initial = {
            'subject': authority.id
        }
        aarelation=AARelation()
        aarelation.subject = authority
        type_controlled = request.GET.get('type_controlled', None)
        if type_controlled:
            aarelation = dict(AARelation.TYPE_CHOICES)[type_controlled]
        form = AARelationForm(prefix='aarelation', instance=aarelation)
    elif request.method == 'POST':
        form = AARelationForm(request.POST, prefix='aarelation')
        if form.is_valid():
            form.save()

            target = reverse('curation:curate_authority', args=(authority.id,)) + '?tab=aarelations'
            if search_key and current_index:
                target += '&search=%s&current=%s' % (search_key, current_index)
            return HttpResponseRedirect(target)

    context.update({
        'form': form,
    })
    template = 'curation/authority_aarelation_changeview.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def acrelation_for_authority(request, authority_id, acrelation_id):
    authority = get_object_or_404(Authority, pk=authority_id)
    acrelation = get_object_or_404(ACRelation, pk=acrelation_id)

    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'acrelation': acrelation,
        'search_key': search_key,
        'current_index': current_index
    }
    if request.method == 'GET':
        form = ACRelationForm(instance=acrelation, prefix='acrelation')

    elif request.method == 'POST':
        form = ACRelationForm(request.POST, instance=acrelation, prefix='acrelation')
        if form.is_valid():
            form.save()
            target = reverse('curation:curate_authority', args=(authority.id,)) + '?tab=acrelations'
            if search_key and current_index:
                target += '&search=%s&current=%s' % (search_key, current_index)
            return HttpResponseRedirect(target)

    context.update({
        'form': form,
    })
    template = 'curation/authority_acrelation_changeview.html'
    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def aarelation_for_authority(request, authority_id, aarelation_id):
    authority = get_object_or_404(Authority, pk=authority_id)
    aarelation = get_object_or_404(AARelation, pk=aarelation_id)

    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'aarelation': aarelation,
        'search_key': search_key,
        'current_index': current_index
    }
    if request.method == 'GET':
        form = AARelationForm(instance=aarelation, prefix='aarelation')

    elif request.method == 'POST':
        form = AARelationForm(request.POST, instance=aarelation, prefix='aarelation')
        if form.is_valid():
            form.save()
            target = reverse('curation:curate_authority', args=(authority.id,)) + '?tab=aarelations'
            if search_key and current_index:
                target += '&search=%s&current=%s' % (search_key, current_index)
            return HttpResponseRedirect(target)

    context.update({
        'form': form,
    })
    template = 'curation/authority_aarelation_changeview.html'
    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def delete_aarelation_for_authority(request, authority_id, aarelation_id, format=None):
    authority = get_object_or_404(Authority, pk=authority_id)
    aarelation = get_object_or_404(AARelation, pk=aarelation_id)
    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'aarelation': aarelation,
        'search_key': search_key,
        'current_index': current_index
    }

    if request.POST.get('confirm', False) == 'true':
        if not aarelation.modified_on:
            aarelation.modified_on = datetime.datetime.now()
        aarelation.delete()
        if format == 'json':
            return JsonResponse({'result': True})

        target = reverse('curation:curate_authority', args=(authority.id,)) + '?tab=aarelations'
        if search_key and current_index:
            target += '&search=%s&current=%s' % (search_key, current_index)
        return HttpResponseRedirect(target)

    if format == 'json':
        return JsonResponse({'result': False})

    template = 'curation/authority_aarelation_delete.html'
    return render(request, template, context)
