from django.shortcuts import render
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, HttpResponseForbidden, Http404, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_protect

from isisdata.models import *

from zotero.models import *
from zotero.suggest import suggest_citation, suggest_authority


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
