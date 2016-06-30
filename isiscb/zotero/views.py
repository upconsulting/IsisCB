from django.shortcuts import render
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, HttpResponseForbidden, Http404, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required, user_passes_test
from django.template import RequestContext, loader

from isisdata.models import *

from zotero.models import *
from zotero.filters import *
from zotero.forms import *
from zotero import parser as zparser
from zotero.suggest import suggest_citation, suggest_authority

import tempfile


@login_required
@csrf_protect
def suggest_citation_json(request, citation_id):
    draftCitation = get_object_or_404(DraftCitation, pk=citation_id)
    suggestions = []
    for suggestion in suggest_citation(draftCitation):
        instance = Citation.objects.get(pk=suggestion['id'])
        suggestion.update({
            'title': instance.title,
            'publication_date': instance.publication_date,
            'type_controlled': instance.type_controlled,
            })
        suggestions.append(suggestion)
    return JsonResponse({'data': suggestions})


@login_required
@csrf_protect
def suggest_authority_json(request, authority_id):
    draftAuthority = get_object_or_404(DraftAuthority, pk=authority_id)
    suggestions = []
    for suggestion in suggest_authority(draftAuthority):
        instance = Authority.objects.get(pk=suggestion['id'])
        suggestion.update({
            'name': instance.name,
            'type_controlled': instance.type_controlled,
            })
        suggestions.append(suggestion)
    return JsonResponse({'data': suggestions})


@login_required
@csrf_protect
def suggest_acrelation_json(request, acrelation_id):
    draftACRelation = get_object_or_404(DraftACRelation, pk=acrelation_id)
    return suggest_authority_json(request, draftACRelation.authority_id)


@login_required
@csrf_protect
def suggest_production_acrelation_json(request, acrelation_id):
    acrelation = get_object_or_404(ACRelation, pk=acrelation_id)
    if acrelation.resolutions.count() < 1:
        draftCitation = acrelation.citation.resolutions.first().for_instance
        draftAuthority = DraftAuthority.objects.create(
            name=acrelation.name_for_display_in_citation,
            part_of=draftCitation.part_of
        )
        draftACRelation = DraftACRelation.objects.create(
            citation=draftCitation,
            authority=draftAuthority,
            part_of=draftCitation.part_of
        )
        InstanceResolutionEvent.objects.create(
            for_instance=draftACRelation,
            to_instance=acrelation
        )
    else:
        draftAuthority = acrelation.resolutions.first().for_instance.authority

    return suggest_authority_json(request, draftAuthority.id)


@staff_member_required
def accessions(request):
    """
    Curator should be able to see a list of Zotero ingests, with indication of
    whether all authorities have been resolved for a batch.
    """

    queryset = ImportAccession.objects.filter(resolved=False)
    filtered_objects = ImportAccesionFilter(request.GET, queryset=queryset)

    context = RequestContext(request, {
        'curation_section': 'zotero',
        'curation_subsection': 'accessions',
        'objects': filtered_objects,
    })
    template = loader.get_template('zotero/accessions.html')
    return HttpResponse(template.render(context))


@staff_member_required
def create_accession(request):
    context = RequestContext(request, {
        'curation_section': 'zotero',
        'curation_subsection': 'accessions',
    })

    template = loader.get_template('zotero/create_accession.html')


    if request.method == 'GET':
        form = ImportAccessionForm()

    elif request.method == 'POST':
        form = ImportAccessionForm(request.POST, request.FILES)
        if form.is_valid():
            instance = form.save()
            instance.imported_by = request.user
            instance.save()

            with tempfile.NamedTemporaryFile(suffix='.rdf', delete=False) as destination:
                destination.write(form.cleaned_data['zotero_rdf'].file.read())
                path = destination.name

            papers = zparser.read(path)
            zparser.process(papers, instance=instance)
    context.update({'form': form})

    return HttpResponse(template.render(context))
