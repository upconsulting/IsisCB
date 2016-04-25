from django.shortcuts import render
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, HttpResponseForbidden, Http404, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required

from isisdata.models import *

from zotero.models import *
from zotero.suggest import suggest_citation, suggest_authority


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
