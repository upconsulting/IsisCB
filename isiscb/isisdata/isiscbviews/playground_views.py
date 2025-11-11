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
    subjects = request['subjects']
    domino_effect = request['domino']
    node_ids = set(subjects.copy())
    
    subject_theses_ids = ACRelation.objects.filter(
            public=True, 
            authority__public=True, 
            citation__public=True, 
            authority__id__in=subjects, 
            citation__type_controlled=Citation.THESIS, 
            type_controlled__in=[ACRelation.SCHOOL, ACRelation.AUTHOR, ACRelation.ADVISOR]
            )\
        .values_list("citation__id", flat=True).distinct("citation__id")

    subject_theses = Citation.objects.filter(id__in=[subject_theses_ids])
  
    nodes = []
    links = []
    
    if subject_theses:
        for thesis in subject_theses:
            extrapolate_thesis(thesis, node_ids, links, domino_effect, subjects)

    node_associations_min = 0
    node_associations_max = 0
                
    if node_ids:
        node_authorities = Authority.objects.filter(pk__in=list(node_ids))
        for authority in node_authorities:
            node, node_association_count = generate_genealogy_node(authority, subjects)
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
        'subjects': subjects,
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

