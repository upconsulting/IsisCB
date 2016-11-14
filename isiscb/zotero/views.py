from django.shortcuts import render
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, HttpResponseForbidden, Http404, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required, user_passes_test
from django.template import RequestContext, loader
from django.core.urlresolvers import reverse

from isisdata.models import *

from curation.contrib.views import check_rules

from zotero.models import *
from zotero.filters import *
from zotero.forms import *
from zotero import tasks, parse, ingest
from zotero.suggest import suggest_citation, suggest_authority

import tempfile


def _field_data(instance):
    return [(k, v) for k, v in instance.__dict__.items() if not k.startswith('_')]


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
        related_citations = instance.acrelation_set.values_list('citation__title', flat=True)[:10]
        suggestion.update({
            'name': instance.name,
            'citation_count': instance.acrelation_set.count(),
            'type_controlled': instance.get_type_controlled_display(),
            'related_citations': list(related_citations),
            })
        suggestions.append(suggestion)
        if len(suggestions) > 30:
            break
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


@check_rules('has_zotero_access')
@staff_member_required
def accessions(request):
    """
    Curator should be able to see a list of Zotero ingests, with indication of
    whether all authorities have been resolved for a batch.
    """

    queryset = ImportAccession.objects.all().order_by('-imported_on')
    filtered_objects = ImportAccesionFilter(request.GET, queryset=queryset)

    context = RequestContext(request, {
        'curation_section': 'zotero',
        'curation_subsection': 'accessions',
        'objects': filtered_objects,
    })
    template = loader.get_template('zotero/accessions.html')
    return HttpResponse(template.render(context))


@check_rules('has_zotero_access')
@staff_member_required
def create_accession(request):
    """
    Curators should be able to upload Zotero RDF.
    """
    context = RequestContext(request, {
        'curation_section': 'zotero',
        'curation_subsection': 'accessions',
    })

    template = loader.get_template('zotero/create_accession.html')

    if request.method == 'GET':
        try:
            initial = {'ingest_to': Dataset.objects.get(name='Isis Bibliography of the History of Science (Stephen P. Weldon, ed.)')}
        except Dataset.DoesNotExist:
            initial = {}

        form = ImportAccessionForm(initial=initial)

    elif request.method == 'POST':
        form = ImportAccessionForm(request.POST, request.FILES)
        if form.is_valid():
            instance = form.save()
            instance.imported_by = request.user
            instance.save()

            with tempfile.NamedTemporaryFile(suffix='.rdf', delete=False) as destination:
                destination.write(form.cleaned_data['zotero_rdf'].file.read())
                path = destination.name

            ingest.IngestManager(parse.ZoteroIngest(path), instance).process()
            return HttpResponseRedirect(reverse('retrieve_accession', args=[instance.id,]))
    context.update({'form': form})

    return HttpResponse(template.render(context))


@check_rules('has_zotero_access')
@staff_member_required
def retrieve_accession(request, accession_id):
    """
    Curator should be able to see a list of all draft authorities in a specific
    Zotero ingest.
    """

    template = loader.get_template('zotero/retrieve_accession.html')
    accession = get_object_or_404(ImportAccession, pk=accession_id)
    context = RequestContext(request, {
        'curation_section': 'zotero',
        'curation_subsection': 'accessions',
        'accession': accession,
    })
    return HttpResponse(template.render(context))


@check_rules('has_zotero_access')
@staff_member_required
def similar_authorities(request):
    accession_id = request.GET.get('accession')
    draftauthority_id = request.GET.get('draftauthority')

    accession = get_object_or_404(ImportAccession, pk=accession_id)
    draftauthority = get_object_or_404(DraftAuthority, pk=draftauthority_id)

    queryset = accession.draftauthority_set.filter(
                        name=draftauthority.name,
                        processed=False,
                        type_controlled=draftauthority.type_controlled)
    queryset = queryset.exclude(pk=draftauthority_id)
    response_data = {
        'count': queryset.count(),
        'draftauthorities': [obj.id for obj in queryset],
    }
    return JsonResponse({'data': response_data})



@check_rules('has_zotero_access')
@staff_member_required
def resolve_authority(request):
    authority_id = request.GET.get('authority')
    draftauthority_id = request.GET.get('draftauthority')

    authority = get_object_or_404(Authority, pk=authority_id)
    draftauthority = get_object_or_404(DraftAuthority, pk=draftauthority_id)

    resolution = InstanceResolutionEvent.objects.create(for_instance=draftauthority, to_instance=authority)
    draftauthority.processed = True
    draftauthority.save()

    return JsonResponse({'data': resolution.id})


@check_rules('has_zotero_access')
@staff_member_required
def skip_authority_for_draft(request):
    draftauthority_id = request.GET.get('draftauthority')
    accession_id = request.GET.get('accession')

    draftauthority = get_object_or_404(DraftAuthority, pk=draftauthority_id)
    accession = get_object_or_404(ImportAccession, pk=accession_id)
    print 'skip_authority_for_draft', draftauthority.id, accession.id
    draftauthority.processed = True
    draftauthority.save()
    return JsonResponse({'data': None})



@check_rules('has_zotero_access')
@staff_member_required
def create_authority_for_draft(request):
    draftauthority_id = request.GET.get('draftauthority')
    accession_id = request.GET.get('accession')

    draftauthority = get_object_or_404(DraftAuthority, pk=draftauthority_id)
    accession = get_object_or_404(ImportAccession, pk=accession_id)

    # Authority instance from field data.
    authority_data = {
        'name': draftauthority.name,
        'type_controlled': draftauthority.type_controlled,
        'public': True,
        'belongs_to': accession.ingest_to,
        'record_status_value': CuratedMixin.ACTIVE,
        'record_status_explanation': u'Active by default.',
        'record_history': tasks._record_history_message(request, accession),
    }

    #  Note: ISISCB-577 Created authority records should be active by default.
    if draftauthority.type_controlled == DraftAuthority.PERSON:
        model_class = Person
        authority_data.update({
            'personal_name_last': draftauthority.name_last if draftauthority.name_last else u'',
            'personal_name_first': draftauthority.name_first if draftauthority.name_first else u'',
            'personal_name_suffix': draftauthority.name_suffix if draftauthority.name_suffix else u'',
            'personal_name_preferred': draftauthority.name,
        })
    else:
        model_class = Authority

    authority = model_class.objects.create(**authority_data)

    resolution = InstanceResolutionEvent.objects.create(for_instance=draftauthority, to_instance=authority)
    draftauthority.processed = True
    draftauthority.save()

    for draftlinkeddata in draftauthority.linkeddata.all():
        ldtype, _ = LinkedDataType.objects.get_or_create(name=draftlinkeddata.name)
        LinkedData.objects.create(
            subject = authority,
            universal_resource_name = draftlinkeddata.value,
            type_controlled = ldtype
        )
    draftauthority.linkeddata.all().update(processed=True)

    response_data = {
        'resolution': resolution.id,
        'authority': authority.id,
    }
    return JsonResponse({'data': response_data})


@check_rules('has_zotero_access')
@staff_member_required
def data_importaccession(request, accession_id):
    template = loader.get_template('zotero/raw_data_list.html')
    accession = get_object_or_404(ImportAccession, pk=accession_id)
    queryset = accession.draftcitation_set.all().order_by('title')


    context = RequestContext(request, {
        'accession': accession,
        'draftcitations':  queryset,
    })
    return HttpResponse(template.render(context))


@check_rules('has_zotero_access')
@staff_member_required
def data_draftcitation(request, draftcitation_id):
    template = loader.get_template('zotero/raw_data.html')
    draftcitation = get_object_or_404(DraftCitation, pk=draftcitation_id)
    data = _field_data(draftcitation)
    related_data = [
        (
            'Authority Records',
            [(_field_data(acrelation), _field_data(acrelation.authority))
             for acrelation in draftcitation.authority_relations.all()]
        )
    ]
    context = RequestContext(request, {
        'curation_section': 'zotero',
        'curation_subsection': 'accessions',
        'instance': draftcitation,
        'data': data,
        'related_data': related_data,
    })
    return HttpResponse(template.render(context))


@check_rules('has_zotero_access')
@staff_member_required
def data_draftauthority(request, draftauthority_id):
    template = loader.get_template('zotero/raw_data.html')
    draftauthority = get_object_or_404(DraftAuthority, pk=draftauthority_id)
    data = _field_data(draftauthority)
    related_data = [
        (
            'Citations',
            [(_field_data(acrelation), _field_data(acrelation.citation))
             for acrelation in draftauthority.citation_relations.all()]
        )
    ]
    context = RequestContext(request, {
        'curation_section': 'zotero',
        'curation_subsection': 'accessions',
        'instance': draftauthority,
        'data': data,
        'related_data': related_data,
    })
    return HttpResponse(template.render(context))


@check_rules('has_zotero_access')
@staff_member_required
def ingest_accession(request, accession_id):
    accession = get_object_or_404(ImportAccession, pk=accession_id)
    queryset = accession.draftcitation_set.all().order_by('title')

    context = RequestContext(request, {
        'curation_section': 'zotero',
        'curation_subsection': 'accessions',
        'accession': accession,
        'draftcitations': queryset,
    })

    confirmed = request.GET.get('confirmed', False)
    if confirmed:
        ingested = tasks.ingest_accession(request, accession)
        context.update({'ingested': ingested})
        template = loader.get_template('zotero/ingest_accession_success.html')
    else:
        template = loader.get_template('zotero/ingest_accession_prompt.html')


    return HttpResponse(template.render(context))


@check_rules('has_zotero_access')
@staff_member_required
def change_draftauthority(request, draftauthority_id):
    authority = get_object_or_404(DraftAuthority, pk=draftauthority_id)
    if request.method == 'POST':
        form = DraftAuthorityForm(request.POST, instance=authority)
        if form.is_valid():
            form.save()
            last = request.GET.get('next', None)
            if last:
                return HttpResponseRedirect(last)
            return HttpResponseRedirect(reverse('data_draftauthority', args=(authority.id,)))
    elif request.method == 'GET':
        form = DraftAuthorityForm(instance=authority)

    context = RequestContext(request, {
        'form': form,
        'authority': authority,
        'next': request.GET.get('next', None)
    })
    template = loader.get_template('zotero/change_draftauthority.html')
    return HttpResponse(template.render(context))
