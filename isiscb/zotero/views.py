from django.shortcuts import render
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, HttpResponseForbidden, Http404, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required, user_passes_test
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
    """
    Provides Authority suggestion data in the authority resolution interface.
    """
    draftAuthority = get_object_or_404(DraftAuthority, pk=authority_id)
    suggestions = []

    for suggestion in suggest_authority(draftAuthority):
        instance = Authority.objects.get(pk=suggestion['id'])

        # Do not suggest inactive records.
        if instance.record_status_value != CuratedMixin.ACTIVE:
            continue

        _type_map = dict(Citation.TYPE_CHOICES)
        def _format_citation(o):
            _title, _title_for_sort, _type_controlled = o
            if _type_controlled == Citation.REVIEW:
                _s = u'Rev. of %s' % _title_for_sort.title()
            else:
                _s = _title.title()
            return _s + u' (%s)' % _type_map.get(_type_controlled)

        related_citations = set(instance.acrelation_set.values_list(
            'citation__title',
            'citation__title_for_sort',
            'citation__type_controlled'
        )[:10])

        suggestion.update({
            'name': instance.name,
            'citation_count': instance.acrelation_set.count(),
            'type_controlled': instance.get_type_controlled_display(),
            'related_citations': map(_format_citation, related_citations),
        })
        suggestions.append(suggestion)

        # Show a maximum of 30 suggestions. TODO: make this configurable.
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

    queryset = ImportAccession.objects.all()
    filtered_objects = ImportAccesionFilter(request.GET, queryset=queryset)

    context = {
        'curation_section': 'zotero',
        'curation_subsection': 'accessions',
        'objects': filtered_objects,
    }
    template = 'zotero/accessions.html'
    return render(request, template, context)


@check_rules('has_zotero_access')
@staff_member_required
def create_accession(request):
    """
    Curators should be able to upload Zotero RDF.
    """
    context = {
        'curation_section': 'zotero',
        'curation_subsection': 'accessions',
    }

    template = 'zotero/create_accession.html'

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

    return render(request, template, context)


@check_rules('has_zotero_access')
@staff_member_required
def retrieve_accession(request, accession_id):
    """
    Curator should be able to see a list of all draft authorities in a specific
    Zotero ingest.
    """

    template = 'zotero/retrieve_accession.html'
    accession = get_object_or_404(ImportAccession, pk=accession_id)
    draftcitations = accession.draftcitation_set.filter(processed=False)

    # ISISCB-1043: show warning if a citation might already be in the db
    matching_citations_ld = {}
    matching_citations_title = {}
    for dcitation in draftcitations:
        matches = []
        linkeddata = DraftCitationLinkedData.objects.filter(citation=dcitation)
        for draft_ld in linkeddata:
            ldtype = LinkedDataType.objects.filter(name=draft_ld.name.upper())
            matching_ld = LinkedData.objects.filter(type_controlled=ldtype, universal_resource_name=draft_ld.value) if ldtype else None
            if matching_ld:
                matches = [match.subject for match in matching_ld]
                break

        if matches:
            matching_citations_ld[dcitation.id] = matches

        possible_matches = Citation.objects.filter(title=dcitation.title)
        if possible_matches:
            matching_citations_title[dcitation.id] = possible_matches

    context = {
        'curation_section': 'zotero',
        'curation_subsection': 'accessions',
        'accession': accession,
        'draftcitations': draftcitations,
        'resolved_draftcitations': accession.draftcitation_set.filter(processed=True),
        'matching_citations_linkeddata': matching_citations_ld,
        'matching_citations_title': matching_citations_title,
    }
    return render(request, template, context)


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
    authority_name = request.GET.get('authority_name')
    authority_first_name = request.GET.get('authority_first_name')
    authority_last_name = request.GET.get('authority_last_name')
    accession_id = request.GET.get('accession')

    draftauthority = get_object_or_404(DraftAuthority, pk=draftauthority_id)
    accession = get_object_or_404(ImportAccession, pk=accession_id)

    # Authority instance from field data.
    authority_data = {
        'name': authority_name if authority_name else draftauthority.name,
        'type_controlled': draftauthority.type_controlled,
        'public': True,
        'belongs_to': accession.ingest_to,
        'record_status_value': CuratedMixin.ACTIVE,
        'record_status_explanation': u'Active by default.',
        'record_history': tasks._record_history_message(request, accession),
    }

    #  Note: ISISCB-577 Created authority records should be active by default.
    if draftauthority.type_controlled == DraftAuthority.PERSON:
        first_name = authority_first_name if authority_first_name else draftauthority.name_first
        last_name = authority_last_name if authority_last_name else draftauthority.name_last
        model_class = Person
        authority_data.update({
            'personal_name_last': last_name if last_name else u'',
            'personal_name_first': first_name if first_name else u'',
            'personal_name_suffix': draftauthority.name_suffix if draftauthority.name_suffix else u'',
            'personal_name_preferred': draftauthority.name,
        })
    else:
        model_class = Authority

    authority = model_class.objects.create(**authority_data)

    # We want generic relations to point to the Authority table rather than the
    #  Person table.
    generic_target = Authority.objects.get(pk=authority.id)

    resolution = InstanceResolutionEvent.objects.create(for_instance=draftauthority, to_instance=authority)
    draftauthority.processed = True
    draftauthority.save()

    for draftlinkeddata in draftauthority.linkeddata.all():

        ldtype, _ = LinkedDataType.objects.get_or_create(name=draftlinkeddata.name.upper())
        l = LinkedData.objects.create(
            subject = generic_target,
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
    template = 'zotero/raw_data_list.html'
    accession = get_object_or_404(ImportAccession, pk=accession_id)
    queryset = accession.draftcitation_set.all().order_by('title')


    context = {
        'accession': accession,
        'draftcitations':  queryset,
    }
    return render(request, template, context)


@check_rules('has_zotero_access')
@staff_member_required
def data_draftcitation(request, draftcitation_id):
    template = 'zotero/raw_data.html'
    draftcitation = get_object_or_404(DraftCitation, pk=draftcitation_id)
    data = _field_data(draftcitation)
    related_data = [
        (
            'Authority Records',
            [(_field_data(acrelation), _field_data(acrelation.authority))
             for acrelation in draftcitation.authority_relations.all()]
        ),
        (
            'Citation Records (from)',
            [(_field_data(ccrelation), _field_data(ccrelation.object))
             for ccrelation in draftcitation.relations_from.all()]
        ),
        (
            'Citation Records (to)',
            [(_field_data(ccrelation), _field_data(ccrelation.subject))
             for ccrelation in draftcitation.relations_to.all()]
        )
    ]
    context = {
        'curation_section': 'zotero',
        'curation_subsection': 'accessions',
        'instance': draftcitation,
        'data': data,
        'related_data': related_data,
    }
    return render(request, template, context)


@check_rules('has_zotero_access')
@staff_member_required
def data_draftauthority(request, draftauthority_id):
    template = 'zotero/raw_data.html'
    draftauthority = get_object_or_404(DraftAuthority, pk=draftauthority_id)
    data = _field_data(draftauthority)
    related_data = [
        (
            'Citations',
            [(_field_data(acrelation), _field_data(acrelation.citation))
             for acrelation in draftauthority.citation_relations.all()]
        )
    ]
    context = {
        'curation_section': 'zotero',
        'curation_subsection': 'accessions',
        'instance': draftauthority,
        'data': data,
        'related_data': related_data,
    }
    return render(request, template, context)


@check_rules('has_zotero_access')
@staff_member_required
def ingest_accession(request, accession_id):
    accession = get_object_or_404(ImportAccession, pk=accession_id)
    queryset = accession.draftcitation_set.all().order_by('title')

    context = {
        'curation_section': 'zotero',
        'curation_subsection': 'accessions',
        'accession': accession,
        'draftcitations': queryset,
    }

    confirmed = request.GET.get('confirmed', False)
    if confirmed:
        ingested = tasks.ingest_accession(request, accession)
        context.update({'ingested': ingested})
        template = 'zotero/ingest_accession_success.html'
    else:
        template = 'zotero/ingest_accession_prompt.html'


    return render(request, template, context)


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

    context = {
        'form': form,
        'authority': authority,
        'next': request.GET.get('next', None)
    }
    template = 'zotero/change_draftauthority.html'
    return render(request, template, context)


@check_rules('has_zotero_access')
@staff_member_required
def remove_draftcitation(request):
    draftcitation = get_object_or_404(DraftCitation,
                                      pk=request.GET.get('citation'))
    draftcitation.delete();
    return JsonResponse({'data': 'ok'});
