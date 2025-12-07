from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render
from django.http import JsonResponse
from isisdata.models import Citation, Authority, ACRelation
from isisdata.forms import ThesisMillForm

from isisdata.playground import *

import json


@ensure_csrf_cookie
def genealogy(request, tenant_id=None):
    context = {}

    if request.method != 'POST':
        return render(request, 'isisdata/genealogy.html', context)
    
    request = json.loads(request.body) 
    selected_subjects = request['subjects']
    domino_effect = request['domino']
    display_subjects = set(selected_subjects.copy())

    # When users select subjects of type concept or geographic term, 
    # the process for producing the network graph data is different 
    # than that for people and institutions. 

    # get selected subject authority objects for concepts and places
    concept_or_geographic_subject_authority_ids = Authority.objects.filter(
            pk__in=selected_subjects, 
            type_controlled__in=[Authority.CONCEPT, Authority.GEOGRAPHIC_TERM]
            )\
        .values_list("id", flat=True)

    # remove any concepts/places from the display subjects because we don't want them
    # in the graph we want to create genealogies from, we want the people who write about them
    display_subjects.difference_update(concept_or_geographic_subject_authority_ids)

    node_ids = set(display_subjects.copy())
    
    # get ACRs for citations that have selected concept/place as subject
    concept_or_geographic_related_citation_ids = None
    if concept_or_geographic_subject_authority_ids:
        concept_or_geographic_related_citation_ids = ACRelation.objects.filter(
                public=True,
                citation__public=True,
                type_controlled=ACRelation.SUBJECT,
                authority__id__in=concept_or_geographic_subject_authority_ids,
                )\
            .values_list("citation__id", flat=True).distinct("citation__id")
    
    # get the top authors of citations about that concept/place
    concept_or_geographic_related_authors = None
    if concept_or_geographic_related_citation_ids:
        concept_or_geographic_related_authors = ACRelation.objects.filter(
                public=True,
                type_controlled=ACRelation.AUTHOR,
                citation__id__in=[concept_or_geographic_related_citation_ids]
                ).values('authority__id')\
            .annotate(author=Count('authority__id')).order_by('-author')\
            .values_list("authority__id", flat=True)[:299]
    
    # add those authors to the display subjects
    if concept_or_geographic_related_authors:
        display_subjects.update(concept_or_geographic_related_authors)
    
    # fetch all ACRs of theses related to our display subjects
    subject_theses_ids = ACRelation.objects.filter(
            public=True, 
            authority__public=True, 
            citation__public=True, 
            authority__id__in=display_subjects, 
            citation__type_controlled=Citation.THESIS, 
            type_controlled__in=[ACRelation.SCHOOL, ACRelation.AUTHOR, ACRelation.ADVISOR]
            )\
        .values_list("citation__id", flat=True).distinct("citation__id")

    # get the theses linked to those ACRs
    subject_theses = Citation.objects.filter(id__in=[subject_theses_ids])
  
    nodes = []
    links = []
    
    if subject_theses:
        for thesis in subject_theses:
            extrapolate_thesis(thesis, node_ids, links, domino_effect, display_subjects)

    node_associations_min = 0
    node_associations_max = 0
                
    if node_ids:
        node_authorities = Authority.objects.filter(pk__in=list(node_ids))
        for authority in node_authorities:
            node, node_association_count = generate_genealogy_node(authority, display_subjects)
            node_associations_min = node_association_count if node_association_count < node_associations_min else node_associations_min
            node_associations_max = node_association_count if node_association_count > node_associations_max else node_associations_max
            nodes.append(node)

    node_associations_range = {
        'min': node_associations_min,
        'max': node_associations_max,
    }

    context = {
        'nodes': json.dumps(nodes),
        'links': json.dumps(links),
        'subjects': list(display_subjects),
        'node_associations_range': node_associations_range,
    }

    return JsonResponse(context)

@ensure_csrf_cookie
def theses_by_school(request, tenant_id=None):
    form = ThesisMillForm()
    top = form.fields['top'].initial
    chart_type = form.fields['chart_type'].initial
    chart_type_urls = {
        "HG": "heatgrid",
        "NA": "normalized-area",
        "AR": "area",
        "ST": "streamgraph",
    }
    select_schools = []
    
    if request.method == 'POST':
        form = ThesisMillForm(request.POST)
        if form.is_valid():
            chart_type = form.cleaned_data["chart_type"]
            top = form.cleaned_data["top"] if form.cleaned_data["top"] == "CU" else int(form.cleaned_data["top"]) 
            select_schools = form.cleaned_data["select_schools"]

    context = generate_theses_by_school_context(top, chart_type, select_schools)       

    context["form"] = form
    context["top"] = top
    context["chart_url"] = chart_type_urls[chart_type]
        
    return render(request, 'isisdata/theses_by_school.html', context)

