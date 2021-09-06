from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

from past.builtins import cmp
from builtins import str
from past.utils import old_div
from django.contrib.admin.views.decorators import staff_member_required, user_passes_test
from django.contrib import messages
from django.core.paginator import EmptyPage

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, QueryDict #, HttpResponseForbidden, Http404, , JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.core.cache import caches
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.http import QueryDict
from django.shortcuts import redirect
from django.utils import formats
from django.utils.http import urlencode
from django.utils.text import slugify
from django.utils.html import escape
from django.template.loader import get_template
from django.db.models import Count

import urllib.parse as urllibparse

from rules.contrib.views import permission_required, objectgetter
from django.forms import modelform_factory, formset_factory

from isisdata.models import *
from isisdata.utils import strip_punctuation, normalize
from isisdata import operations
from isisdata.filters import *
from isisdata import tasks as data_tasks
from curation import p3_port_utils


from curation.tracking import TrackingWorkflow
from zotero.models import ImportAccession

from curation.forms import *

from curation.contrib.views import check_rules
from curation import tasks as curation_tasks
import curation.view_helpers as view_helpers

from haystack.query import SearchQuerySet

import iso8601, rules, datetime, hashlib, math
from itertools import chain
from unidecode import unidecode
import bleach
import datetime

import logging

PAGE_SIZE = 40    # TODO: this should be configurable.


def _get_datestring_for_authority(authority):
    return ', '.join([attribute.value.display for attribute in authority.attributes.all()])


def _get_datestring_for_citation(citation):
    if citation.publication_date:
        return citation.publication_date.isoformat()[:4]
    return 'missing'


def _get_citation_title(citation):
    title = citation.title
    if not title:
        for relation in citation.ccrelations:
            if relation.type_controlled in [CCRelation.REVIEW_OF, CCRelation.REVIEWED_BY]:
                return u'Review: %s' % relation.subject.title if relation.subject.id != citation.id else relation.object.title
        return u'Untitled review'
    return title


def _get_authors_editors(citation):
    return ', '.join([getattr(relation.authority, 'name', 'missing') + ' ('+  relation.get_type_controlled_display() + ')' for relation in citation.acrelations
                if relation.type_controlled in [ACRelation.AUTHOR, ACRelation.EDITOR]])

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def dashboard(request):
    """
    """
    template = 'curation/dashboard.html'
    context = {}
    return render(request, template, context)



@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def datasets(request):
    """
    """
    template = 'curation/dashboard.html'
    context = {
        'curation_section':'datasets',
    }
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
#@check_rules('can_create_record')
def create_citation(request):

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
    }

    template = 'curation/citation_create_view.html'

    if request.method == 'GET':
        form = CitationForm(user=request.user)

        context.update({
            'form': form,
        })
        partdetails_form = PartDetailsForm(request.user)
        context.update({
            'partdetails_form': partdetails_form,
        })
    elif request.method == 'POST':
        form = CitationForm(request.user, request.POST)
        partdetails_form = PartDetailsForm(request.user, citation_id = None, data=request.POST)

        if form.is_valid() and partdetails_form.is_valid():
            form.cleaned_data['public'] = False
            #form.cleaned_data['record_status_value'] = CuratedMixin.INACTIVE why does this not work?
            citation = form.save()
            citation.record_status_value = CuratedMixin.INACTIVE
            citation.save()

            if partdetails_form:
                partdetails_form.save()
            return HttpResponseRedirect(reverse('curation:curate_citation', args=(citation.id,)))
        else:
            context.update({
                'form' : form,
                'partdetails_form': partdetails_form,
            })

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
#@check_rules('can_create_record')
def create_authority(request):
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
    }
    if request.GET.get('draft_authority_id', None) and request.GET.get('zotero_accession', None):
        context.update({
            'authority_name': request.GET.get('name', None),
            'draft_authority_id': request.GET.get('draft_authority_id', None),
            'zotero_accession': request.GET.get('zotero_accession', None),
            'selected_authority_type': request.GET.get('selected_authority_type', None),
        })
    if request.POST.get('draft_authority_id', None) and request.POST.get('zotero_accession', None):
        context.update({
            'authority_name': request.POST.get('name', None),
            'draft_authority_id': request.POST.get('draft_authority_id', None),
            'zotero_accession': request.POST.get('zotero_accession', None),
            'selected_authority_type': request.POST.get('selected_authority_type', None),
        })

    template = 'curation/authority_create_view.html'


    value_forms = view_helpers._create_attribute_value_forms()

    if request.method == 'GET':
        form = AuthorityForm(user=request.user, prefix='authority')
        person_form = PersonForm(request.user, authority_id=None, prefix='person')
        attribute_form = AttributeForm(prefix="attribute")
        daterange_form = modelform_factory(ISODateRangeValue,
                                exclude=('attribute', 'child_class'))
        linkeddata_form = LinkedDataForm(prefix='linkeddata')

        context.update({
            'form': form,
            'person_form': person_form,
            'attribute_form': attribute_form,
            'linkeddata_form': linkeddata_form,
            'value_forms': [(i, f(prefix='value')) for i, f in list(value_forms.items())],
        })
    elif request.method == 'POST':
        authority = Authority()
        person_form = None
        if request.POST.get('authority-type_controlled', '') == Authority.PERSON:
            authority = Person()
            person_form = PersonForm(request.user, None, request.POST, prefix='person', instance=authority)

        form = AuthorityForm(request.user, request.POST, prefix='authority', instance=authority)

        linkeddata_form = None
        linkeddata_urm = request.POST.get('linkeddata-universal_resource_name', None)
        linkeddata_type = request.POST.get("linkeddata-type_controlled", None)
        if linkeddata_urm and linkeddata_type:
            linkeddata_form = LinkedDataForm(request.POST, prefix='linkeddata')

        attribute_form = None
        value_form = None
        if request.POST.get("attribute-type_controlled", ''):
            selected_attr_type_controlled = request.POST.get('attribute-type_controlled', None)
            attr_freeform = request.POST.get('attribute-value_freeform', None)
            if selected_attr_type_controlled and attr_freeform:
                attribute_form = AttributeForm(request.POST, prefix='attribute')
                attribute_form.instance.record_status_value = CuratedMixin.ACTIVE
                value_form_class = value_forms[int(selected_attr_type_controlled)]
                value_form = value_form_class(request.POST, prefix='value')
        if form.is_valid() and (person_form is None or person_form.is_valid()) and (linkeddata_form is None or linkeddata_form.is_valid()) and (attribute_form is None or (attribute_form.is_valid() and value_form and value_form.is_valid())):
            if person_form:
                person_form.save()

            form.cleaned_data['public'] = False
            form.cleaned_data['record_status_value'] = CuratedMixin.INACTIVE
            form.instance.created_by_stored = request.user
            authority = form.save()

            if linkeddata_form:
                # we need to make sure the subjec type is authority, or the generic relations don't work
                linkeddata_form.instance.subject = Authority.objects.get(pk=authority.id)
                linkeddata_form.save()

            if attribute_form:
                attribute_form.instance.source = Authority.objects.get(pk=authority.id)
                attribute_form.instance.modified_by = request.user
                attribute_form.instance.save()

                value_form.instance.attribute = attribute_form.instance
                attribute_form.instance.source = authority

                value_form.save()

            zotero_accession = request.POST.get('zotero_accession', None)
            draft_authority_id = request.POST.get('draft_authority_id', None)
            # if we're in a zotero ingest procedure
            if zotero_accession:
                return HttpResponseRedirect("%s?draft_authority_id=%s&resolved_authority_id=%s&resolved_authority_name=%s" % (reverse('retrieve_accession', args=(zotero_accession,)), draft_authority_id, authority.id, authority.name))
            return HttpResponseRedirect(reverse('curation:curate_authority', args=(authority.id,)))
        else:
            context.update({
                'form' : form,
                'person_form': person_form if person_form else PersonForm(request.user, authority_id=None, prefix='person'),
                'attribute_form': attribute_form if attribute_form else AttributeForm(prefix="attribute"),
                'linkeddata_form': linkeddata_form if linkeddata_form else LinkedDataForm(prefix='linkeddata'),
                'value_form': value_form,
                'value_forms': [(i, f(prefix='value')) for i, f in list(value_forms.items())],
            })
    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def get_subject_suggestions(request, citation_id):
    authority_id = request.GET.get('authority_id', None)
    sqs = SearchQuerySet().facet('subject_ids', size=100)
    suggestion_results = sqs.all().filter_or(author_ids__eq=authority_id).filter_or(contributor_ids__eq=authority_id) \
            .filter_or(editor_ids__eq=authority_id).filter_or(subject_ids=authority_id).filter_or(institution_ids=authority_id) \
            .filter_or(category_ids=authority_id).filter_or(advisor_ids=authority_id).filter_or(translator_ids=authority_id) \
            .filter_or(publisher_ids=authority_id).filter_or(school_ids=authority_id).filter_or(meeting_ids=authority_id) \
            .filter_or(periodical_ids=authority_id).filter_or(book_series_ids=authority_id).filter_or(time_period_ids=authority_id) \
            .filter_or(geographic_ids=authority_id).filter_or(about_person_ids=authority_id).filter_or(other_person_ids=authority_id) \

    suggestion_results = suggestion_results.facet_counts()['fields']['subject_ids']
    suggestion_results_ids = [s[0] for s in suggestion_results]
    authorities = Authority.objects.filter(pk__in=suggestion_results_ids).values('id','name', 'type_controlled')
    suggestion_results_dict = dict(suggestion_results)
    for authority in authorities:
        authority['count'] = suggestion_results_dict[authority['id']]
        authority['type'] = dict(Authority.TYPE_CHOICES)[authority['type_controlled']]
    authorities = sorted(authorities, key=lambda auth: auth['count'], reverse=True)
    response_data = {
        'subjects': list(authorities)
    }
    return JsonResponse(response_data)


# TODO this method needs to be logged down!
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def quick_create_acrelation(request):
    if request.method == 'POST':
        authority_id = request.POST.get('authority_id')
        citation_id = request.POST.get('citation_id')
        type_controlled = request.POST.get('type_controlled')
        type_broad_controlled = request.POST.get('type_broad_controlled')
        instance = ACRelation.objects.create(
            authority_id=authority_id,
            citation_id=citation_id,
            type_controlled=type_controlled,
            type_broad_controlled=type_broad_controlled,
            public=True,
            record_status_value=CuratedMixin.ACTIVE,
        )

        response_data = {
            'acrelation': {
                'id': instance.id,
                'type_controlled': instance.type_controlled,
                'get_type_controlled_display': instance.get_type_controlled_display(),
                'type_broad_controlled': instance.type_broad_controlled,
                'authority': {
                    'id': instance.authority.id,
                    'name': instance.authority.name,
                    'type_controlled': instance.authority.type_controlled,
                },
                'citation': {
                    'id': instance.citation.id,
                    'name': _get_citation_title(instance.citation),
                    'type_controlled': instance.citation.type_controlled,
                },
            }
        }
        return JsonResponse(response_data)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def create_ccrelation_for_citation(request, citation_id):
    citation = get_object_or_404(Citation, pk=citation_id)
    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))
    is_object = request.GET.get('is_object', 'false')

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'search_key': search_key,
        'current_index': current_index
    }
    if request.method == 'GET':
        ccrelation = CCRelation()
        initial={}
        if citation.type_controlled == Citation.CHAPTER or is_object == 'true':
            ccrelation.object = citation
            ccrelation.type_controlled = CCRelation.INCLUDES_CHAPTER
            initial['type_controlled'] = CCRelation.INCLUDES_CHAPTER
            initial['object'] = citation.id
        else:
            initial['subject'] = citation.id
            ccrelation.subject = citation
        form = CCRelationForm(prefix='ccrelation', initial=initial, instance=ccrelation)
        context.update({
            'ccrelation': ccrelation,
        })

    elif request.method == 'POST':
        form = CCRelationForm(request.POST, prefix='ccrelation')
        if form.is_valid():
            form.save()
            target = reverse('curation:curate_citation', args=(citation.id,)) + '?'
            if search_key and current_index:
                target += '&search=%s&current=%s' % (search_key, current_index)
            return HttpResponseRedirect(target)

    context.update({
        'form': form,
    })
    template = 'curation/citation_ccrelation_changeview.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def ccrelation_for_citation(request, citation_id, ccrelation_id=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    ccrelation = None if not ccrelation_id else get_object_or_404(CCRelation, pk=ccrelation_id)
    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'ccrelation': ccrelation,
        'search_key': search_key,
        'current_index': current_index
    }
    if request.method == 'GET':
        if ccrelation:
            form = CCRelationForm(instance=ccrelation, prefix='ccrelation')
        else:
            form = CCRelationForm(prefix='ccrelation', initial={'subject': citation.id})

    elif request.method == 'POST':
        form = CCRelationForm(request.POST, instance=ccrelation, prefix='ccrelation')
        if form.is_valid():
            form.save()
            target = reverse('curation:curate_citation', args=(citation.id,)) + '?'
            if search_key and current_index:
                target += '&search=%s&current=%s' % (search_key, current_index)
            return HttpResponseRedirect(target)

    context.update({
        'form': form,
    })
    template = 'curation/citation_ccrelation_changeview.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def create_acrelation_for_citation(request, citation_id):
    citation = get_object_or_404(Citation, pk=citation_id)

    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'search_key': search_key,
        'current_index': current_index
    }
    if request.method == 'GET':
        initial = {
            'citation': citation.id,
        }
        type_controlled = request.GET.get('type_controlled', None)
        if type_controlled:
            initial.update({'type_controlled': type_controlled.upper()})
        form = ACRelationForm(prefix='acrelation', initial=initial)

    elif request.method == 'POST':
        form = ACRelationForm(request.POST, prefix='acrelation')
        if form.is_valid():
            form.save()
            target = reverse('curation:curate_citation', args=(citation.id,)) + '?'
            if search_key and current_index:
                target += '&search=%s&current=%s' % (search_key, current_index)
            return HttpResponseRedirect(target)

    context.update({
        'form': form,
    })
    template = 'curation/citation_acrelation_changeview.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def acrelation_for_citation(request, citation_id, acrelation_id=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    acrelation = None if not acrelation_id else get_object_or_404(ACRelation, pk=acrelation_id)

    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'acrelation': acrelation,
        'search_key': search_key,
        'current_index': current_index
    }
    if request.method == 'GET':
        form = ACRelationForm(instance=acrelation, prefix='acrelation')

    elif request.method == 'POST':
        form = ACRelationForm(request.POST, instance=acrelation, prefix='acrelation')
        if form.is_valid():
            form.instance.modified_by = request.user
            form.save()
            target = reverse('curation:curate_citation', args=(citation.id,)) + '?'
            if search_key and current_index:
                target += '&search=%s&current=%s' % (search_key, current_index)
            return HttpResponseRedirect(target)

    context.update({
        'form': form,
    })
    template = 'curation/citation_acrelation_changeview.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def tracking_for_citation(request, citation_id):
    citation = get_object_or_404(Citation, pk=citation_id)

    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'search_key': search_key,
        'current_index': current_index
    }

    if request.method == "POST":
        search_key = request.POST.get('search', request.POST.get('search'))
        current_index = request.POST.get('current', request.POST.get('current'))
        trackType = request.POST.get('type', None)
        tracking = Tracking()
        tracking.type_controlled = trackType
        tracking.modified_by = request.user
        date = datetime.datetime.now()
        tracking.tracking_info = date.strftime("%Y/%m/%d") + " {} {}".format(request.user.first_name, request.user.last_name)
        tracking.citation = citation
        tracking.save()
        citation.save()

    target = reverse('curation:curate_citation', args=(citation_id,)) + '?tab=tracking'
    if search_key and current_index:
        target += '&search=%s&current=%s' % (search_key, current_index)
    return HttpResponseRedirect(target)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def tracking_for_authority(request, authority_id):
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

    template = 'curation/authority_tracking_create.html'

    if request.method == "POST":
        form = AuthorityTrackingForm(request.POST, instance=AuthorityTracking(), prefix='tracking')
        if form.is_valid():
            tracking = form.save(commit=False)
            tracking.authority = authority
            tracking.save()
            authority.tracking_state = tracking.type_controlled
            authority.save()
            target = reverse('curation:curate_authority', args=(authority_id,)) + '?tab=tracking'
            if search_key and current_index:
                target += '&search=%s&current=%s' % (search_key, current_index)
            return HttpResponseRedirect(target)
    else:
        # just always shows tracking form if not post
        form = AuthorityTrackingForm(prefix='tracking', initial={'subject': authority_id})

    context.update({
        'form': form,
    })

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def delete_attribute_for_citation(request, citation_id, attribute_id, format=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    attribute = get_object_or_404(Attribute, pk=attribute_id)
    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'attribute': attribute,
        'search_key': search_key,
        'current_index': current_index
    }
    if request.GET.get('confirm', False):
        attribute.delete()
        if format == 'json':
            return JsonResponse({'result': True})
        target = reverse('curation:curate_citation', args=(citation.id,)) + '?tab=attributes'
        if search_key and current_index:
            target += '&search=%s&current=%s' % (search_key, current_index)
        return HttpResponseRedirect(target)
    template = 'curation/citation_attribute_delete.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def delete_linkeddata_for_citation(request, citation_id, linkeddata_id, format=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    linkeddata = get_object_or_404(LinkedData, pk=linkeddata_id)
    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'linkeddata': linkeddata,
        'search_key': search_key,
        'current_index': current_index
    }

    if request.GET.get('confirm', False):
        linkeddata.delete()

        if format == 'json':
            return JsonResponse({'result': True})

        target = reverse('curation:curate_citation', args=(citation.id,)) + '?tab=linkeddata'
        if search_key and current_index:
            target += '&search=%s&current=%s' % (search_key, current_index)
        return HttpResponseRedirect(target)
    template = 'curation/citation_linkeddata_delete.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def delete_linkeddata_for_authority(request, authority_id, linkeddata_id, format=None):
    authority = get_object_or_404(Authority, pk=authority_id)
    linkeddata = get_object_or_404(LinkedData, pk=linkeddata_id)
    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'linkeddata': linkeddata,
        'search_key': search_key,
        'current_index': current_index
    }

    if request.GET.get('confirm', False):
        linkeddata.delete()

        if format == 'json':
            return JsonResponse({'result': True})

        target = reverse('curation:curate_authority', args=(authority.id,)) + '?tab=linkeddata'
        if search_key and current_index:
            target += '&search=%s&current=%s' % (search_key, current_index)
        return HttpResponseRedirect(target)
    template = 'curation/authority_linkeddata_delete.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def delete_language_for_citation(request, citation_id):
    # TODO: format?
    citation = get_object_or_404(Citation, pk=citation_id)
    language_id = request.GET.get('language', None)
    if not language_id:
        raise Http404

    citation.language.remove(language_id)
    citation.save()
    return JsonResponse({'result': True})


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def add_language_for_citation(request, citation_id):
    # TODO: format?
    citation = get_object_or_404(Citation, pk=citation_id)
    language_id = request.POST.get('language', None)
    if not language_id:
        raise Http404

    language = get_object_or_404(Language, pk=language_id)
    citation.language.add(language)
    citation.save()
    result = {
        'language': {
            'id': language_id,
            'name':language.name
        }
    }
    return JsonResponse(result)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def delete_ccrelation_for_citation(request, citation_id, ccrelation_id, format=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    ccrelation = get_object_or_404(CCRelation, pk=ccrelation_id)
    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'ccrelation': ccrelation,
        'search_key': search_key,
        'current_index': current_index
    }
    if request.GET.get('confirm', False):
        ccrelation.delete()
        if format == 'json':
            return JsonResponse({'result': True})

        target = reverse('curation:curate_citation', args=(citation.id,)) + '?'
        if search_key and current_index:
            target += '&search=%s&current=%s' % (search_key, current_index)
        return HttpResponseRedirect(target)
    template = 'curation/citation_ccrelation_delete.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def delete_acrelation_for_citation(request, citation_id, acrelation_id, format=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    acrelation = get_object_or_404(ACRelation, pk=acrelation_id)
    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'acrelation': acrelation,
        'search_key': search_key,
        'current_index': current_index
    }
    if request.GET.get('confirm', False):
        if not acrelation.modified_on:
            acrelation.modified_on = datetime.datetime.now()
        acrelation.delete()
        if format == 'json':
            return JsonResponse({'result': True})

        target = reverse('curation:curate_citation', args=(citation.id,)) + '?'
        if search_key and current_index:
            target += '&search=%s&current=%s' % (search_key, current_index)
        return HttpResponseRedirect(target)
    template = 'curation/citation_acrelation_delete.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def delete_acrelation_for_authority(request, authority_id, acrelation_id, format=None):
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
    if request.GET.get('confirm', False):
        if not acrelation.modified_on:
            acrelation.modified_on = datetime.datetime.now()
        acrelation.delete()
        if format == 'json':
            return JsonResponse({'result': True})

        target = reverse('curation:curate_authority', args=(authority.id,)) + '?tab=acrelations'
        if search_key and current_index:
            target += '&search=%s&current=%s' % (search_key, current_index)
        return HttpResponseRedirect(target)
    template = 'curation/authority_acrelation_delete.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def delete_attribute_for_authority(request, authority_id, attribute_id, format=None):
    authority = get_object_or_404(Authority, pk=authority_id)
    attribute = get_object_or_404(Attribute, pk=attribute_id)
    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'attribute': attribute,
        'search_key': search_key,
        'current_index': current_index
    }
    if request.GET.get('confirm', False):
        attribute.delete()
        if format == 'json':
            return JsonResponse({'result': True})

        target = reverse('curation:curate_authority', args=(authority.id,)) + '?tab=attributes'
        if search_key and current_index:
            target += '&search=%s&current=%s' % (search_key, current_index)
        return HttpResponseRedirect(target)
    template = 'curation/authority_attribute_delete.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def linkeddata_for_citation(request, citation_id, linkeddata_id=None):

    template = 'curation/citation_linkeddata_changeview.html'
    citation = get_object_or_404(Citation, pk=citation_id)

    linkeddata = None

    if linkeddata_id:
        linkeddata = get_object_or_404(LinkedData, pk=linkeddata_id)

    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'linkeddata': linkeddata,
        'search_key': search_key,
        'current_index': current_index,
    }

    if request.method == 'GET':
        if linkeddata:
            linkeddata_form = LinkedDataForm(instance=linkeddata,
                                             prefix='linkeddata')
        else:
            initial = {}
            type_controlled = request.GET.get('type_controlled', None)
            if type_controlled:
                q = {'name__istartswith': type_controlled}
                qs = LinkedDataType.objects.filter(**q)
                if qs.count() > 0:
                    initial.update({'type_controlled': qs.first()})

            linkeddata_form = LinkedDataForm(prefix='linkeddata',
                                             initial=initial)
    elif request.method == 'POST':
        if linkeddata:    # Update.
            linkeddata_form = LinkedDataForm(request.POST, instance=linkeddata, prefix='linkeddata')
        else:    # Create.
            linkeddata_form = LinkedDataForm(request.POST, prefix='linkeddata')

        if linkeddata_form.is_valid():
            linkeddata_form.instance.subject = citation
            linkeddata_form.save()

            target = reverse('curation:curate_citation', args=(citation.id,)) + '?'
            if search_key and current_index:
                target += '&search=%s&current=%s' % (search_key, current_index)
            return HttpResponseRedirect(target)
        else:
            pass
    else:
        redirect('curation:curate_citation', citation_id)

    context.update({
        'linkeddata_form': linkeddata_form,
    })
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def linkeddata_for_authority(request, authority_id, linkeddata_id=None):

    template = 'curation/authority_linkeddata_changeview.html'
    authority = get_object_or_404(Authority, pk=authority_id)
    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))
    linkeddata = None

    if linkeddata_id:
        linkeddata = get_object_or_404(LinkedData, pk=linkeddata_id)

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': authority,
        'linkeddata': linkeddata,
        'search_key': search_key,
        'current_index': current_index,
    }

    if request.method == 'GET':
        if linkeddata:
            linkeddata_form = LinkedDataForm(instance=linkeddata, prefix='linkeddata')
        else:
            linkeddata_form = LinkedDataForm(prefix='linkeddata')
    elif request.method == 'POST':
        if linkeddata:    # Update.
            linkeddata_form = LinkedDataForm(request.POST, instance=linkeddata, prefix='linkeddata')
        else:    # Create.
            linkeddata_form = LinkedDataForm(request.POST, prefix='linkeddata')

        if linkeddata_form.is_valid():
            linkeddata_form.instance.subject = authority
            linkeddata_form.save()

            target = reverse('curation:curate_authority', args=(authority.id,)) + '?tab=linkeddata'
            if search_key and current_index:
                target += '&search=%s&current=%s' % (search_key, current_index)
            return HttpResponseRedirect(target)
        else:
            pass
    else:
        redirect('curation:curate_authority', authority_id)

    context.update({
        'linkeddata_form': linkeddata_form,
    })
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def attribute_for_citation(request, citation_id, attribute_id=None):

    template = 'curation/citation_attribute_changeview.html'
    citation = get_object_or_404(Citation, pk=citation_id)
    attribute, value, value_form, value_form_class = None, None, None, None
    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))

    value_forms = view_helpers._create_attribute_value_forms()

    if attribute_id:
        attribute = get_object_or_404(Attribute, pk=attribute_id)
        if hasattr(attribute, 'value'):
            value = attribute.value.get_child_class()
            value_form_class = value_forms[attribute.type_controlled.id]

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'attribute': attribute,
        'value': value,
        'search_key': search_key,
        'current_index': current_index
    }

    if request.method == 'GET':
        if attribute:
            attribute_form = AttributeForm(instance=attribute, prefix='attribute')
            if value:
                value_form = value_form_class(instance=value, prefix='value')
        else:
            attribute_form = AttributeForm(prefix='attribute')

    elif request.method == 'POST':
        if attribute:    # Update.
            attribute_form = AttributeForm(request.POST, instance=attribute, prefix='attribute')

            value_instance = value if value else None
            value_form = value_form_class(request.POST, instance=value_instance, prefix='value')
        else:    # Create.
            attribute_form = AttributeForm(request.POST, prefix='attribute')
            selected_type_controlled = request.POST.get('attribute-type_controlled', None)
            if selected_type_controlled is not None:
                value_form_class = value_forms[int(selected_type_controlled)]
                value_form = value_form_class(request.POST, prefix='value')

        if attribute_form.is_valid() and value_form and value_form.is_valid():
            attribute_form.instance.source = citation
            attribute_form.save()
            value_form.instance.attribute = attribute_form.instance
            value_form.save()
            if not attribute_form.instance.value_freeform:
                attribute_form.instance.value_freeform = value_form.instance.render()
                attribute_form.instance.save()

            target = reverse('curation:curate_citation', args=(citation.id,)) + '?'
            if search_key and current_index:
                target += '&search=%s&current=%s' % (search_key, current_index)
            return HttpResponseRedirect(target)
        else:
            pass

    context.update({
        'attribute_form': attribute_form,
        'value_form': value_form,
        'value_forms': [(i, f(prefix='value')) for i, f in list(value_forms.items())],
    })
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def attribute_for_authority(request, authority_id, attribute_id=None):

    country_code_attribute = settings.COUNTRY_CODE_ATTRIBUTE

    template = 'curation/authority_attribute_changeview.html'
    authority = get_object_or_404(Authority, pk=authority_id)
    attribute, value, value_form, value_form_class = None, None, None, None
    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))

    value_forms = view_helpers._create_attribute_value_forms()

    if attribute_id:
        attribute = get_object_or_404(Attribute, pk=attribute_id)
        if hasattr(attribute, 'value'):
            value = attribute.value.get_child_class()
            value_form_class = value_forms[attribute.type_controlled.id]

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'attribute': attribute,
        'country_code_attribute': country_code_attribute,
        'value': value,
        'search_key': search_key,
        'current_index': current_index
    }

    if request.method == 'GET':
        if attribute:
            attribute_form = AttributeForm(instance=attribute, prefix='attribute')
            if value:
                value_form = value_form_class(instance=value, prefix='value')
        else:
            attribute_form = AttributeForm(prefix='attribute')


    elif request.method == 'POST':
        if attribute:    # Update.
            attribute_form = AttributeForm(request.POST, instance=attribute, prefix='attribute')

            value_instance = value if value else None
            value_form = value_form_class(request.POST, instance=value_instance, prefix='value')
        else:    # Create.
            attribute_form = AttributeForm(request.POST, prefix='attribute')
            selected_type_controlled = request.POST.get('attribute-type_controlled', None)
            if selected_type_controlled:
                value_form_class = value_forms[int(selected_type_controlled)]
                value_form = value_form_class(request.POST, prefix='value')

        if attribute_form.is_valid() and value_form and value_form.is_valid():
            attribute_form.instance.source = authority
            attribute_form.instance.modified_by = request.user
            attribute_form.save()

            attribute_form.instance.save()
            value_form.instance.attribute = attribute_form.instance
            value_form.save()

            target = reverse('curation:curate_authority', args=(authority.id,)) + '?tab=attributes'
            if search_key and current_index:
                target += '&search=%s&current=%s' % (search_key, current_index)
            return HttpResponseRedirect(target)
        else:
            pass

    context.update({
        'attribute_form': attribute_form,
        'value_form': value_form,
        'value_forms': [(i, f(prefix='value')) for i, f in list(value_forms.items())],
    })
    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def get_attribute_type_help_text(request, attribute_type_id):
    print(attribute_type_id)
    attribute_type = get_object_or_404(AttributeType, pk=attribute_type_id)

    safe_text = bleach.clean(attribute_type.attribute_help_text, strip=True)
    return JsonResponse({'help_text': safe_text})

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def citation(request, citation_id):
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'type_choices': Citation.TYPE_CHOICES,
        'publisher_distributor_types': ACRelation.TYPE_CATEGORY_PUB_DISTR,
        'personal_responsibility_types': ACRelation.PERSONAL_RESPONS_TYPES,
        'date_attribute_types': [DateTimeValue, ISODateRangeValue, DateRangeValue, ISODateValue, DateValue],
        'ccrel_contained_relations': [CCRelation.INCLUDES_CHAPTER, CCRelation.INCLUDES_SERIES_ARTICLE, CCRelation.INCLUDES_CITATION_OBJECT, CCRelation.REVIEWED_BY],
        'ccrel_related_citations': [CCRelation.ASSOCIATED_WITH],
        'responsibility_mapping': ACRelation.RESPONSIBILITY_MAPPING,
        'acrel_type_choices': dict(ACRelation.TYPE_CHOICES),
        'host_mapping': ACRelation.HOST_MAPPING,
        'publication_date_attribute_name': settings.TIMELINE_PUBLICATION_DATE_ATTRIBUTE,
        'accessed_date_attribute_name': settings.ACCESSED_ATTRIBUTE_NAME,
        'doi_linked_date_name': settings.DOI_LINKED_DATA_NAME,
        'isbn_linked_date_name': settings.ISBN_LINKED_DATA_NAME,
    }

    start = datetime.datetime.now()

    citation = get_object_or_404(Citation, pk=citation_id)
    _build_result_set_links(request, context)

    # we now use only one template for all types IEXP-15
    template = 'curation/citation_change_view.html'

    partdetails_form = None
    context.update({'tab': request.GET.get('tab', None)})
    if request.method == 'GET':
        form = CitationForm(user=request.user, instance=citation)
        tracking_records = citation.tracking_records.all() #Tracking.objects.filter(subject_instance_id=citation_id)

        tracking_workflow = TrackingWorkflow(citation)
        context.update({
            'form': form,
            'instance': citation,
            'tracking_records': tracking_records,
            'can_create_fully_entered': tracking_workflow.is_workflow_action_allowed(Tracking.FULLY_ENTERED),
            'can_create_proofed': tracking_workflow.is_workflow_action_allowed(Tracking.PROOFED),
            'can_create_authorize': tracking_workflow.is_workflow_action_allowed(Tracking.AUTHORIZED),
        })

        part_details = getattr(citation, 'part_details', None)
        if not part_details:
            part_details = PartDetails.objects.create()
            citation.part_details = part_details
            citation.save()

        partdetails_form = PartDetailsForm(request.user, citation_id,
                                           instance=part_details,
                                           prefix='partdetails')
        context.update({
            'partdetails_form': partdetails_form,
        })
    elif request.method == 'POST':
        form = CitationForm(request.user, request.POST, instance=citation)
        if hasattr(citation, 'part_details'):
            partdetails_form = PartDetailsForm(request.user, citation_id, request.POST, prefix='partdetails', instance=citation.part_details)
        if form.is_valid() and (partdetails_form is None or partdetails_form.is_valid()):
            form.save()
            if partdetails_form:
                partdetails_form.save()

            search = request.POST.get('search')
            current_index = request.POST.get('current')

            forward_type = request.POST.get('forward_type', None)
            if forward_type == "list":
                return HttpResponseRedirect(reverse('curation:citation_list') + "?search=%s&page=%s" % (search, str(page)))
            if forward_type == "next":
                target_object = context.get('next', citation)
                target_index = context.get('next_index', current_index)
            elif forward_type == "previous":
                target_object = context.get('previous', citation)
                target_index = context.get('previous_index', current_index)
            else:
                target_object = citation.id
                target_index = current_index

            target = reverse('curation:curate_citation', args=(target_object,))
            if search and target_index:
                target += '?search=%s&current=%s' % (search, target_index)
            return HttpResponseRedirect(target)
            # return HttpResponseRedirect()

        context.update({
            'form': form,
            'instance': citation,
            'partdetails_form': partdetails_form,
        })

    return render(request, template, context)


# TODO: needs updated doc
def _build_result_set_links(request, context, model=Citation):
    """
    This function build all the info that the previous/next/back to list links from  a given
    request object, context object for the page, and the citation that should be displayed.
    After calling this method, the context object will have five additional properties:
    * next: the next citation in the result set
    * previous: the previous citation in the result set
    * index: the current position in the result set
    * request_params: request parameters that went into the function call
    * total: the total number of found citations
    """
    start = datetime.datetime.now()

    user_session = request.session
    model_key = model.__name__.lower()
    search_key = request.GET.get('search', request.POST.get('search'))
    current_index = request.GET.get('current', request.POST.get('current'))
    search_params = user_session.get('%s_%s_search_params' % (search_key, model_key))
    search_count = user_session.get('%s_%s_search_count' % (search_key, model_key))

    # If there is no search, or we arrive at a record without a position in
    #  the search results, there is nothing to do.
    if not search_key or not current_index or not search_params:
        return

    current_index = int(current_index)
    page_number = int(math.floor(old_div(current_index, PAGE_SIZE))) + 1
    relative_index = current_index % PAGE_SIZE

    # The "current run" is the series of record IDs on the current page.
    # The "prior" and "antecedent" are the IDs of the last record on the
    # previous page and the first record on the next page, respectively.
    current_run = user_session.get('%s_%s_page_%i' % (str(search_key), model_key, page_number))
    prior = user_session.get('%s_%s_current_prior_%i' % (str(search_key), model_key, page_number))
    antecedent = user_session.get('%s_%s_current_antecedent_%i' % (str(search_key), model_key, page_number))

    if current_run is None:
        queryset = operations.filter_queryset(request.user, model.objects.all())
        filter_class = eval('%sFilter' % model.__name__.title())
        if model == Citation:
            filtered_objects = filter_class(search_params, queryset=queryset.select_related('part_details'))
        else:
            filtered_objects = filter_class(search_params, queryset=queryset)
        paginator = Paginator(filtered_objects.qs, PAGE_SIZE)
        page = paginator.page(page_number)

        current_run = [o.id for o in page]
        prior_page = paginator.page(page_number - 1) if page_number > 1 else []
        antecedent_page = paginator.page(page_number + 1) if paginator.page(page_number).has_next() else []

        try:
            prior = prior_page[0].id
        except IndexError:
            prior = None
        try:
            antecedent = antecedent_page[-1].id
        except IndexError:
            antecedent = None

        user_session['%s_%s_page_%i' % (str(search_key), model_key, page_number)] = current_run
        user_session['%s_%s_current_prior_%i' % (str(search_key), model_key, page_number)] = prior
        user_session['%s_%s_current_antecedent_%i' % (str(search_key), model_key, page_number)] = antecedent

    if current_index == 0:
        prev_id = None
        prev_index = None
    else:
        prev_index = current_index - 1
        prev_id = current_run[relative_index - 1] if relative_index > 0 else prior

    try:
        next_id = current_run[relative_index + 1]
    except IndexError:
        next_id = antecedent

    # if there is a following record, set next index
    next_index = current_index + 1 if next_id else None


    context.update({
        'next': next_id,
        'next_index': next_index,
        'previous': prev_id,
        'previous_index': prev_index,
        'total': search_count,
        'current_index': current_index,
        'index': current_index + 1,
        'search_key': search_key,
        'current_page': page_number,
        'current_offset': (page_number - 1) * PAGE_SIZE
    })

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def change_record_type(request, citation_id):
    citation = get_object_or_404(Citation, pk=citation_id)

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
    }

    target = reverse('curation:curate_citation', args=(citation_id,))
    if request.method == 'POST':
        new_type = request.POST.get('type_controlled', None)
        if dict(Citation.TYPE_CHOICES).get(new_type, None):
            citation.type_controlled = new_type
            citation.save();

        if request.POST.get('search', None) and request.POST.get('current', None):
            target += '?search=%s&current=%s' % (request.POST.get('search', None), request.POST.get('current', None))

    return HttpResponseRedirect(target)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def citation_linkeddata_duplicates(request, citation_id):
    citation = get_object_or_404(Citation, pk=citation_id)

    context = {
        'citation': citation,
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'search': request.GET.get('search', None),
        'current': request.GET.get('current', None),
    }

    linkeddata_entries = citation.linkeddata_entries.all()
    unique_entries, duplicate_entries = find_duplicates(linkeddata_entries)

    context.update({
        'unique_entries': unique_entries,
        'duplicate_entries': duplicate_entries,
    })

    template = 'curation/citation_linkeddata_duplicates.html'

    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def authority_linkeddata_duplicates(request, authority_id):
    authority = get_object_or_404(Authority, pk=authority_id)

    context = {
        'authority': authority,
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'search': request.GET.get('search', None),
        'current': request.GET.get('current', None),
    }

    linkeddata_entries = authority.linkeddata_entries.all()
    unique_entries, duplicate_entries = find_duplicates(linkeddata_entries)

    context.update({
        'unique_entries': unique_entries,
        'duplicate_entries': duplicate_entries,
    })

    template = 'curation/authority_linkeddata_duplicates.html'

    return render(request, template, context)

def find_duplicates(linkeddata_entries):
    unique_entries = {}
    duplicate_entries = []

    for ld in linkeddata_entries:
        key = str(ld.type_controlled) + "_" + str(ld.universal_resource_name)
        if key not in unique_entries:
            unique_entries[key] = ld
        else:
            duplicate_entries.append(ld)

    return unique_entries, duplicate_entries

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def citation_delete_linkeddata_duplicates(request, citation_id):
    citation = get_object_or_404(Citation, pk=citation_id)

    context = {
        'citation': citation,
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
    }

    target = reverse('curation:curate_citation', args=(citation_id,)) + '?tab=linkeddata'
    if request.method == 'POST':
        delete_duplicates(request.POST.get('delete_ids', ''))
        if request.POST.get('search', None) and request.POST.get('current', None):
            target += '&search=%s&current=%s' % (request.POST.get('search', None), request.POST.get('current', None))

    return HttpResponseRedirect(target)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def authority_delete_linkeddata_duplicates(request, authority_id):
    authority = get_object_or_404(Authority, pk=authority_id)

    context = {
        'authority': authority,
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
    }

    target = reverse('curation:curate_authority', args=(authority_id,)) + '?tab=linkeddata'
    if request.method == 'POST':
        delete_duplicates(request.POST.get('delete_ids', ''))
        if request.POST.get('search', None) and request.POST.get('current', None):
            target += '&search=%s&current=%s' % (request.POST.get('search', None), request.POST.get('current', None))

    return HttpResponseRedirect(target)

def delete_duplicates(deleted_ids):
    for ld_id in deleted_ids.split(','):
        if ld_id.strip():
            linkeddata = get_object_or_404(LinkedData, pk=ld_id)
            linkeddata.delete()

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def subjects_and_categories(request, citation_id):
    citation = get_object_or_404(Citation, pk=citation_id)

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
    }

    _build_result_set_links(request, context, Citation)

    template = 'curation/citation_subjects_categories.html'

    return render(request, template, context)



def _authorities_get_filter_params(request):
    """
    Build ``filter_params`` for GET request in authority list view.
    """

    if request.method == 'POST':
        post_or_get = request.POST
    else:
        post_or_get = request.GET

    search_key = post_or_get.get('search')

    additional_params_names = ["page"]
    all_params = {}

    user_session = request.session
    filter_params = None
    if search_key:
        filter_params = user_session.get('%s_authority_search_params' % search_key)
        if filter_params:
            all_params = {k: v for k, v in list(filter_params.items())}

    if len(list(post_or_get.keys())) <= 1:
        if filter_params is None:
            filter_params = user_session.get('authority_filter_params', None)
            all_params = user_session.get('authority_request_params', None)
        if filter_params is not None and all_params is not None:
            # page needs to be updated otherwise it keeps old page count
            if post_or_get.get('page'):
                all_params['page'] = post_or_get.get('page')
            return filter_params, all_params

    if filter_params is None:
        raw_params = post_or_get.urlencode()#.encode('utf-8')
        filter_params = QueryDict(raw_params, mutable=True)

    if not all_params:
        all_params = {}

    if search_key is None:
        if not 'o' in list(filter_params.keys()):
            filter_params['o'] = 'name_for_sort'
        for key in additional_params_names:
            all_params[key] = post_or_get.get(key, '')

        if 'o' not in filter_params:
            filter_params['o'] = 'name_for_sort'
        elif isinstance(filter_params['o'], list):
            if len(filter_params['o']) > 0:
                filter_params['o'] = filter_params['o'][0]
            else:
                filter_params['o'] = 'name_for_sort'

    for key in additional_params_names:
        all_params[key] = post_or_get.get(key, '')
    return filter_params, all_params


def _citations_get_filter_params(request):
    """
    Build ``filter_params`` for GET request in citation list view.
    """


    if request.method == 'POST':
        post_or_get = request.POST
    else:
        post_or_get = request.GET

    search_key = post_or_get.get('search')

    all_params = {}
    additional_params_names = ["page", "zotero_accession", "in_collections",
                               'collection_only', 'show_filters']
    user_session = request.session
    filter_params = None
    if search_key:
        filter_params = user_session.get('%s_citation_search_params' % search_key)
        if filter_params:
            all_params = {k: v for k, v in list(filter_params.items())}

    # if we don't have any filters set yet, or there is just one parameter 'page'
    if len(list(post_or_get.keys())) == 0 or (len(list(post_or_get.keys())) == 1 and post_or_get.get('page', None)):
        if filter_params is None:
            filter_params = user_session.get('citation_filter_params', None)
            all_params = user_session.get('citation_request_params', None)
        if filter_params is not None and all_params is not None:
            # page needs to be updated otherwise it keeps old page count
            if post_or_get.get('page'):
                all_params['page'] = post_or_get.get('page')
            return filter_params, all_params

    if filter_params is None:
        raw_params = post_or_get.urlencode()#.encode('utf-8')
        filter_params = QueryDict(raw_params, mutable=True)

    if not all_params:
        all_params = {}

    if search_key is None:
         if 'o' in filter_params and isinstance(filter_params['o'], list):
             if len(filter_params['o']) > 0:
                 filter_params['o'] = filter_params['o'][0]
             else:
                 filter_params['o'] = "publication_date"

    for key in additional_params_names:
        all_params[key] = post_or_get.get(key, '')

    # Let the GET parameter override the cached POST parameter, in case the
    #  curator is originating in the collections view.
    if "in_collections" in all_params:
        filter_params["in_collections"] = all_params["in_collections"]
    return filter_params, all_params


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def citations(request):
    template = 'curation/citation_list_view.html'

    user_session = request.session
    # We need to be able to amend the filter parameters, so we create a new
    #  mutable QueryDict from the POST payload.
    #  - ``filter_params`` are the parameters that will be passed to the
    #     CitationFilter.
    #  - ``all_params`` includes the parameters in ``filter_params`` plus any
    #     additional parameters not used by the CitationFilter (e.g. page).
    filter_params, all_params = _citations_get_filter_params(request)

    # We use the filter parameters in this form to specify the queryset for
    #  bulk actions.
    if isinstance(filter_params, QueryDict):
        encoded_params = filter_params.urlencode().encode('utf-8')
    else:
        _params = QueryDict(mutable=True)
        for k, v in [k_v for k_v in list(filter_params.items()) if k_v[1] is not None]:
            _params[k] = v
        encoded_params = _params.urlencode().encode('utf-8')

    # In order to isolate search result progressions, we generate a unique key
    #  for this particular set of search results. The search key refers to the
    #  filter and sort parameters, but _not_ the page number.
    search_key = hashlib.md5(encoded_params).hexdigest()

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'filter_params': urllibparse.urlencode(filter_params, quote_via=urllibparse.quote_plus),
        'search_key': search_key,
        'show_filters': all_params['show_filters'] if 'show_filters' in all_params else 'False',
        'record_status_redirect': CuratedMixin.REDIRECT,
        'ccrelation_choices': [(choice, value) for (choice, value) in CCRelation.TYPE_CHOICES if choice is not CCRelation.REVIEW_OF],
    }

    # ISISCB-1157: don't show any result if there are no filters set
    # (or filters are only 'page, 'show_filters, or 'o')
    active_filters = [k for k,v in list(filter_params.items()) if v and k not in ['page', 'show_filters', 'o', 'filters']]

    if not active_filters:
        context.update({
            'objects': CitationFilter(filter_params, queryset=Citation.objects.none()),
            'current_offset': 0,
        })
        return render(request, template, context)

    queryset = operations.filter_queryset(request.user, Citation.objects.all())

    fields = ('record_status_value', 'id', 'type_controlled', 'public',
              'tracking_state', 'modified_on', 'created_native',
              'publication_date', 'title_for_display', 'part_details_id',
              'part_details__page_begin', 'part_details__page_end',
              'part_details__pages_free_text', 'part_details__volume_free_text',
              'part_details__issue_free_text', 'created_on_fm',
              'created_by_native', 'created_by_native__first_name', 'created_by_native__last_name',
              'modified_by__first_name', 'modified_by__last_name', 'modified_by', 'stub_record_status' )

    qs = queryset.select_related('part_details').values(*fields)
    filtered_objects = CitationFilter(filter_params, queryset=qs)

    paginator = Paginator(filtered_objects.qs, PAGE_SIZE)
    currentPage = all_params.get('page', 1)
    if not currentPage:
        currentPage = 1
    currentPage = int(currentPage)
    page = paginator.page(currentPage)
    paginated_objects = list(page)

    if filtered_objects.form.is_valid():
        request_params = filtered_objects.form.cleaned_data
        all_params.update(request_params)

        user_session['citation_filter_params'] = filter_params
        user_session['citation_request_params'] = all_params
        user_session['citation_page'] = int(currentPage)

    result_count = filtered_objects.qs.count()
    user_session['%s_citation_search_params' % str(search_key)] = filter_params
    user_session['%s_citation_search_count' % str(search_key)] = result_count
    user_session['%s_citation_page_%i' % (str(search_key), currentPage)] = [o['id'] for o in paginated_objects]
    user_session['%s_citation_current_prior_%i' % (str(search_key), currentPage)] = paginator.page(currentPage - 1)[-1]['id'] if currentPage > 1 else None
    try:
        user_session['%s_citation_current_antecedent_%i' % (str(search_key), currentPage)] = paginator.page(currentPage + 1)[0]['id']
    except EmptyPage:
        user_session['%s_citation_current_antecedent_%i' % (str(search_key), currentPage)] = None

    context.update({
        'objects': filtered_objects,
        # 'filters_active': filters_active,
        'result_count': result_count,
        'filter_list': paginated_objects,
        'current_page': currentPage,
        'current_offset': (currentPage - 1) * PAGE_SIZE,
        'page': page,
        'paginator': paginator,
    })
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def authorities(request):
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'object_type': 'AUTHORITY',
        'record_status_redirect': CuratedMixin.REDIRECT,
    }

    user_session = request.session

    filter_params, all_params = _authorities_get_filter_params(request)

    if isinstance(filter_params, QueryDict):
        encoded_params = filter_params.urlencode().encode('utf-8')
    else:
        _params = QueryDict(mutable=True)
        for k, v in [k_v1 for k_v1 in list(filter_params.items()) if k_v1[1] is not None]:
            _params[k] = v
        encoded_params = _params.urlencode().encode('utf-8')

    # In order to isolate search result progressions, we generate a unique key
    #  for this particular set of search results. The search key refers to the
    #  filter and sort parameters, but _not_ the page number.
    search_key = hashlib.md5(encoded_params).hexdigest()

    template = 'curation/authority_list_view.html'
    fields = ('id', 'name', 'type_controlled', 'public', 'record_status_value',
              'tracking_state', 'modified_on', 'modified_on_fm',
              'modified_by__first_name', 'modified_by__last_name', 'modified_by',
              'created_by_stored', 'created_by_stored__last_name', 'created_by_stored__first_name',
              'created_on_stored')

    # ISISCB-1157: don't show any result if there are no filters set
    # (or filters are only 'page, 'show_filters, or 'o')
    active_filters = [k for k,v in list(filter_params.items()) if v and k not in ['page', 'show_filters', 'o', 'filters']]

    if not active_filters:
        context.update({
            'objects': AuthorityFilter(filter_params, queryset=Authority.objects.none()),
            'show_filters': all_params['show_filters'] if 'show_filters' in all_params else 'False',
            'current_offset': 0,
        })
        return render(request, template, context)

    queryset = operations.filter_queryset(request.user,
                                          Authority.objects.select_related('linkeddata_entries').values(*fields))

    filtered_objects = AuthorityFilter(filter_params, queryset=queryset)
    result_count = filtered_objects.qs.count()

    paginator = Paginator(filtered_objects.qs, PAGE_SIZE)
    currentPage = all_params.get('page', 1)
    if not currentPage:
        currentPage = 1
    currentPage = int(currentPage)
    page = paginator.page(currentPage)
    paginated_objects = list(page)

    filters_active = filter_params or len([v for k, v in list(request.GET.items()) if len(v) > 0 and k != 'page']) > 0

    if filtered_objects.form.is_valid():
        request_params = filtered_objects.form.cleaned_data
        for key in request_params:
            all_params[key] = request_params[key]

        user_session['authority_request_params'] = all_params
        user_session['authority_filters'] = request_params
        user_session['authority_page'] = int(currentPage)
        user_session['authority_prev_index'] = None

    result_count = filtered_objects.qs.count()
    user_session['%s_authority_search_params' % str(search_key)] = filter_params
    user_session['%s_authority_search_count' % str(search_key)] = result_count
    user_session['%s_authority_page_%i' % (str(search_key), currentPage)] = [o['id'] for o in paginated_objects]
    user_session['%s_authority_current_prior_%i' % (str(search_key), currentPage)] = paginator.page(currentPage - 1)[-1]['id'] if currentPage > 1 else None
    try:
        user_session['%s_authority_current_antecedent_%i' % (str(search_key), currentPage)] = paginator.page(currentPage + 1)[0]['id']
    except EmptyPage:
        user_session['%s_authority_current_antecedent_%i' % (str(search_key), currentPage)] = None

    context.update({
        'objects': filtered_objects,
        'filters_active': filters_active,
        'filter_params': urllibparse.urlencode(filter_params, quote_via=urllibparse.quote_plus),
        'filter_list': paginated_objects,
        'search_key': search_key,
        'result_count': result_count,
        'current_page': currentPage,
        'current_offset': (currentPage - 1) * PAGE_SIZE,
        'show_filters': all_params['show_filters'] if 'show_filters' in all_params else 'False',
        'page': page,
        'paginator': paginator,
    })
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def authority(request, authority_id):
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'country_code_attribute': settings.COUNTRY_CODE_ATTRIBUTE,
    }

    context.update({'tab': request.GET.get('tab', None)})
    authority = get_object_or_404(Authority, pk=authority_id)
    template = 'curation/authority_change_view.html'

    person_form = None
    if request.method == 'GET':

        user_session = request.session
        page = user_session.get('authority_page', 1)
        get_request = user_session.get('authority_filters', {})

        # Something odd going on with the sorting field (``o``).
        if 'o' in get_request and isinstance(get_request['o'], list):
            if len(get_request['o']) > 0:
                get_request['o'] = get_request['o'][0]
            else:
                get_request['o'] = "name_for_sort"

        request_params = user_session.get('authority_request_params', "")

        if authority.type_controlled == Authority.PERSON and hasattr(Authority, 'person'):
            try:
                person_form = PersonForm(request.user, authority_id, instance=authority.person)
            except Person.DoesNotExist:
                person_form = PersonForm(request.user, authority_id)

        form = AuthorityForm(request.user, instance=authority, prefix='authority')

        tracking_records = authority.tracking_records.all() #Tracking.objects.filter(subject_instance_id=authority_id)

        # if zotero_accession is None, we need to remove it or the filters give us trouble
        if not get_request.get('zotero_accession', ''):
            get_request['zotero_accession'] = ''

        # to avoid scripting attacks let's escape the parameters
        safe_get_request = {}
        for key, value in list(get_request.items()):
            safe_get_request[escape(key)] = escape(value)
        context.update({
            'request_params': request_params,
            'filters': safe_get_request,
            'form': form,
            'instance': authority,
            'acrelations': authority.acrelation_set.all()[0:20],
            'aarelations': authority.aarelations_all.all()[0:20],
            'end': 20,
            'total_acrelations': authority.acrelation_set.count(),
            'total_aarelations': authority.aarelations_all.count(),
            'person_form': person_form,
            'tracking_records': tracking_records,
            # 'total': filtered_objects.qs.count(),
        })

    elif request.method == 'POST':
        # check if type was changed to Person
        # if it was changed from person to something else, we'll just keep it a person object for now
        if request.POST.get('authority-type_controlled', '') == Authority.PERSON and authority.type_controlled != Authority.PERSON:
            try:
                # is object already a person
                authority.person
            except Person.DoesNotExist:
                # if not make it one
                person = Person(authority_ptr_id=authority.pk)
                person.__dict__.update(authority.__dict__)
                person.save()
        if authority.type_controlled == Authority.PERSON and hasattr(Authority, 'person'):
            try:
                person_form = PersonForm(request.user, authority_id, request.POST, instance=authority.person)
            except Person.DoesNotExist:
                person_form = None

        form = AuthorityForm(request.user, request.POST, instance=authority, prefix='authority')
        if form.is_valid() and (person_form is None or person_form.is_valid()):
            if person_form:
                person_form.save()

            form.save()

            target = reverse('curation:curate_authority', args=[authority.id,])
            search = request.POST.get('search')
            current = request.POST.get('current')

            if search and current:
                target += '?search=%s&current=%s' % (search, current)
            return HttpResponseRedirect(target)

        context.update({
            'form': form,
            'person_form': person_form,
            'instance': authority,
            # 'partdetails_form': partdetails_form,
        })
    _build_result_set_links(request, context, model=Authority)
    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def authority_acrelations(request, authority_id):
    authority = get_object_or_404(Authority, pk=authority_id)
    template = 'curation/authority_acrelations.html'
    context = {
        'instance': authority,
    }

    start = int(request.GET.get('start', 0))
    nr_of_acrelations = int(request.GET.get('nr', 0))

    acrelation_count = authority.acrelation_set.count()
    acrelations = []
    if start <= acrelation_count:
        end = start + nr_of_acrelations if start + nr_of_acrelations < acrelation_count else acrelation_count
        acrelations = authority.acrelation_set.all()[start:end]
        context.update({
            'acrelations': acrelations,
            'start': start,
            'end': end,
            'total_acrelations': acrelation_count,
        })
    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def quick_and_dirty_language_search(request):
    q = request.GET.get('q', None)
    if not q or len(q) < 3:    # TODO: this should be configurable in the GET.
        return JsonResponse({'results': []})
    queryset = Language.objects.filter(name__istartswith=q)
    results = [{
        'id': language.id,
        'name': language.name,
        'public': True,
    } for language in queryset[:20]]
    return JsonResponse({'results': results})

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def quick_and_dirty_authority_search(request):
    """
    This method searches authorities. It accepts the following paramters:
    * show_inactive: show only active and inactive records; if set to 'false' only
      active records are shown; default is 'true'
    * active_types: for some authority types show only active records; accepts
      comma-separated list of authority types
    * type: limit the search to certain authority types; accepts
      comma-separated list of authority types
    * exclude: exclude certain authority types
    * system: limits results to specified classification systems (comma-separated list)
      system_types: if set, inverses filter for 'system' (excludes records within specified
      classification systems)
    * system_blank: allows classification system to be not set (default is 'true')
    * max: maximal number of results (default is 10)
    * use_custom_cmp: if set to true, uses a custom compare function for ordering results;
      default is 'false'.
      Custom ordering works as follows:
        * First, sort by closeness of match as follows:
            * exact match;
            * whole word match;
            * partial word match from beginning of word.
        * Second, sort by number of linked items.
            * Names without double-hyphens go first
            * If there are names with double-hyphens and the next character is numeric,
              sort in descending numerical order
            * If there are names with double-hyphens and the next character is alpha,
              sort in ascending alphabetical order
      default sorting is as follows:
      * exact matches
      * matches that start with the search phrase
      * matches that contain all parts of the search phrase
      * everything else
      each of these result sets is sorted by the number of linked citations
    """

    q = request.GET.get('q', None)
    show_inactive = request.GET.get('show_inactive', 'true') == 'true'

    # In some cases, the curator wants to limit to active only for certain
    #  authority types.
    limit_active_types = request.GET.get('active_types', None)
    type_controlled = request.GET.get('type', None)
    exclude = request.GET.get('exclude', None)

    # In some cases, the curator wants to apply the system parameter only to
    #  specific authority types.
    limit_clasification_types = request.GET.get('system_types', None)
    classification_system = request.GET.get('system', None)

    force = request.GET.get('force', 'false') == 'true'
    system_blank = request.GET.get('system_blank', 'true') == 'true'
    N = int(request.GET.get('max', 10))
    if not q or (len(q) < 3 and not force):     # TODO: this should be configurable in the GET.
        return JsonResponse({'results': []})

    use_custom_cmp = request.GET.get('use_custom_cmp', 'false') == 'true'

    query = Q()
    if type_controlled:
        type_array = [t.upper() for t in type_controlled.split(",")]
        query &= Q(type_controlled__in=type_array)

    if limit_active_types:
        type_array = [t.upper() for t in limit_active_types.split(",")]
        query &= ~(Q(type_controlled__in=type_array) & Q(record_status_value=CuratedMixin.INACTIVE))

    if exclude:     # exclude certain types
        exclude_array = [t.upper() for t in exclude.split(",")]
        query &= ~Q(type_controlled__in=exclude_array)

    if classification_system:   # filter by classification system
        system_array = [t.upper() for t in classification_system.split(",")]
        if limit_clasification_types:
            type_array = [t.upper() for t in limit_clasification_types.split(",")]
            q_part = Q(type_controlled__in=type_array) & ~Q(classification_system__in=system_array)
            if system_blank:
                q_part &= ~Q(classification_system__isnull=True)
            query &= ~q_part
        else:
            q_part = Q(classification_system__in=system_array)
            if system_blank:
                q_part = q_part | Q(classification_system__isnull=True)
            query &= q_part

    if not show_inactive:   # Don't show inactive records.
        query &= Q(record_status_value=CuratedMixin.ACTIVE)

    queryset = Authority.objects.filter(query)
    queryset_sw = Authority.objects.filter(query)       # Starts with...
    queryset_exact = Authority.objects.filter(query)    # Exact match.
    queryset_with_numbers = Authority.objects.filter(query)    # partial matches, in chunks; with punctuation and numbers.

    # letting the database transform queryies using UPPER prohibits using the index, which is slooowwwww
    # CHECK: removed ur
    query_parts = re.sub('[0-9]+', u' ', strip_punctuation(q)).split()
    for part in query_parts:
        #queryset = queryset.filter(Q(name__icontains=part) | Q(name_for_sort__icontains=unidecode(part)))
        queryset = queryset.filter(Q(name_for_sort__contains=unidecode(part.lower())))

    query_parts_numbers = strip_punctuation(q).split()
    for part in query_parts_numbers:
        #queryset_with_numbers = queryset_with_numbers.filter(name__icontains=part)
        queryset_with_numbers = queryset_with_numbers.filter(name_for_sort__contains=part.lower())

    #queryset_sw = queryset_sw.filter(name_for_sort__istartswith=q).exclude(Q(name_for_sort__iexact=q) | Q(name__iexact=q))
    queryset_sw = queryset_sw.filter(name_for_sort__startswith=q.lower()).exclude(Q(name_for_sort__exact=q.lower()))
    #queryset_exact = queryset_exact.filter(Q(name_for_sort__iexact=q) | Q(name__iexact=q))
    queryset_exact = queryset_exact.filter(Q(name_for_sort__exact=q.lower()))

    # we don't need to duplicate results we've already captured with other queries
    #queryset = queryset.exclude(name_for_sort__istartswith=q).exclude(Q(name_for_sort__iexact=q) | Q(name__iexact=q))
    queryset = queryset.exclude(name_for_sort__startswith=q.lower()).exclude(Q(name_for_sort__exact=q.lower()))

    def _is_int(val):
        try:
            int(val)
            return True
        except:
            return False

    def custom_cmp(a, b):
        if '--' in a.name and '--' in b.name:
            a_remainder = a.name.split('--')[1].strip()
            b_remainder = b.name.split('--')[1].strip()

            # If there are names with double-hyphens and the next character is
            #  numeric, sort in descending numerical order
            if _is_int(a_remainder[0]) and _is_int(b_remainder[0]):
                _v = int(b_remainder[0]) - int(a_remainder[0])
                if _v == 0:
                    if _is_int(a_remainder[0:2]) and _is_int(b_remainder[0:2]):
                        return int(b_remainder[0:2]) - int(a_remainder[0:2])
                    elif _is_int(a_remainder[0:2]):
                        return -1
                    elif _is_int(b_remainder[0:2]):
                        return 1
                    else:
                        return 0
                else:
                    return _v
            # Numeric fragments should go first (e.g. 21st century).
            elif _is_int(a_remainder[0]):
                return -1
            elif _is_int(b_remainder[0]):
                return 1
            else:
                # If there are names with double-hyphens and the next
                #  character is alpha, sort in ascending alphabetical
                #  order.
                return cmp(a_remainder, b_remainder)

        # Names without double-hyphens go first.
        elif '--' in a.name:
            return 1
        elif '--' in b.name:
            return -1
        else:
            return a.acrelation_set.count() - b.acrelation_set.count()

    if use_custom_cmp:
        chained = chain(sorted(queryset_exact, key=p3_port_utils.cmp_to_key(custom_cmp)),
                        sorted(queryset_sw, key=p3_port_utils.cmp_to_key(custom_cmp)),
                        sorted(queryset_with_numbers, key=p3_port_utils.cmp_to_key(custom_cmp)),
                        sorted(queryset, key=p3_port_utils.cmp_to_key(custom_cmp)))
    else:
        chained = chain(queryset_exact.annotate(acrel_count=Count('acrelation')).order_by('-acrel_count'),
                        queryset_sw.annotate(acrel_count=Count('acrelation')).order_by('-acrel_count'),
                        queryset_with_numbers.annotate(acrel_count=Count('acrelation')).order_by('-acrel_count'),
                        queryset.annotate(acrel_count=Count('acrelation')).order_by('-acrel_count'))

    results = []
    result_ids = []

    # first exact matches then starts with matches and last contains matches
    for i, obj in enumerate(chained):    # .order_by('name')
        # there are duplicates since everything that starts with a term
        # also contains the term.
        if obj.id in result_ids:
            # make sure we still return 10 results although we're skipping one
            N += 1
            continue
        if i == N:
            break

        result_ids.append(obj.id)
        results.append({
            'id': obj.id,
            'type': obj.get_type_controlled_display(),
            'type_code': obj.type_controlled,
            'name': obj.name,
            'description': obj.description,
            'related_citations': [s.title() for s in set(obj.acrelation_set.values_list('citation__title_for_sort', flat=True)[:10])],
            'citation_count': obj.acrelation_set.count(),
            'datestring': _get_datestring_for_authority(obj),
            'url': reverse("curation:curate_authority", args=(obj.id,)),
            'public': obj.public,
            'type_controlled': obj.get_type_controlled_display()
        })

    return JsonResponse({'results': results})


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def dataset(request, dataset_id=None):
    return HttpResponse('')


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def search_citation_collections(request):
    return _search_collections(request, CitationCollection)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def search_authority_collections(request):
    return _search_collections(request, AuthorityCollection)

def _search_collections(request, collection_class):
    q = request.GET.get('query', None)
    queryset = collection_class.objects.filter(name__icontains=q)
    results = [{
        'id': col.id,
        'label': col.name,
    } for col in queryset[:20]]
    return JsonResponse(results, safe=False)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def search_zotero_accessions(request):
    q = request.GET.get('query', None)
    queryset = ImportAccession.objects.filter(name__icontains=q)
    results = [{
        'id': accession.id,
        'label': accession.name,
        'date': accession.imported_on
    } for accession in queryset[:20]]
    return JsonResponse(results, safe=False)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def search_linked_data_type(request):
    q = request.GET.get('query', None)
    queryset = LinkedDataType.objects.filter(name__icontains=q)
    results = [{
        'id': ld_type.id,
        'label': ld_type.name,
    } for ld_type in queryset[:20]]
    return JsonResponse(results, safe=False)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def search_datasets(request):
    q = request.GET.get('query', None)
    queryset = Dataset.objects.filter(name__icontains=q)
    results = [{
        'id': ds.id,
        'label': ds.name,
    } for ds in queryset[:20]]
    return JsonResponse(results, safe=False)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def search_users(request):
    q = request.GET.get('query', None)
    if q:
        q = q.strip()
    queryset = User.objects.all().filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    results = [{
        'id': u.id,
        'label': "%s %s (%s)" % (u.first_name, u.last_name, u.username)
    } for u in queryset[:20]]
    return JsonResponse(results, safe=False)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def get_citation_by_id(request):
    id = request.GET.get('id', None)
    if not id:
        return JsonResponse({'citation': None})

    citation = Citation.objects.filter(id=id).first()
    if not citation:
        return JsonResponse({}, status=404)
    return JsonResponse({
        'id': citation.id,
        'title': citation.title_for_display,
    })

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def quick_and_dirty_citation_search(request):
    q = request.GET.get('q', None)
    N = int(request.GET.get('max', 20))
    if not q or len(q) < 3:
        return JsonResponse({'results': []})

    # ISISCB-1132: ccr relations do not find titles with hyphens etc
    q = normalize(q)

    queryset = Citation.objects.all()
    queryset_exact = Citation.objects.all()
    queryset_sw = Citation.objects.all()
    queryset_by_id = Citation.objects.all()

    queryset_exact = queryset_exact.filter(title_for_sort=q)
    queryset_sw = queryset_sw.filter(title_for_sort__istartswith=q)
    queryset_by_id = queryset_by_id.filter(id=q)

    for part in q.split():
        queryset = queryset.filter(title_for_sort__icontains=part)

    queryset = queryset.order_by('title_for_sort')
    queryset_exact = queryset_exact.order_by('title_for_sort')
    queryset_sw = queryset_sw.order_by('title_for_sort')

    result_ids = []
    results = []
    in_publication_types = [ACRelation.PERIODICAL, ACRelation.BOOK_SERIES]
    chapter_types = [CCRelation.INCLUDES_CHAPTER]
    for i, obj in enumerate(chain(queryset_by_id, queryset_exact, queryset_sw, queryset)):
        # there are duplicates since everything that starts with a term
        # also contains the term.
        if obj.id in result_ids:
            # make sure we still return 10 results although we're skipping one
            N += 1
            continue
        if i == N:
            break

        journal = ""
        if obj.type_controlled == Citation.ARTICLE:
            journal_obj = obj.acrelation_set.filter(type_controlled__in=in_publication_types)
            if journal_obj and journal_obj.first() and journal_obj.first().authority:
                journal = journal_obj.first().authority.name

        book = ""
        if obj.type_controlled == Citation.CHAPTER:
            book_obj = obj.ccrelations.filter(type_controlled__in=chapter_types)
            if book_obj and book_obj.first():
                book = book_obj.first().subject.title

        result_ids.append(obj.id)
        results.append({
            'id': obj.id,
            'type': obj.get_type_controlled_display(),
            'type_id':obj.type_controlled,
            'title': _get_citation_title(obj),
            'authors': _get_authors_editors(obj),
            'datestring': _get_datestring_for_citation(obj),
            'description': obj.description,
            'journal': journal,
            'book': book,
            'url': reverse("curation:curate_citation", args=(obj.id,)),
            'public':obj.public,
        })

    return JsonResponse({'results': results})


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def change_is_staff(request, user_id):

    if request.method == 'POST':
        user = get_object_or_404(User, pk=user_id)

        is_staff = request.POST.get('is_staff', False)
        if is_staff == 'True':
            user.is_staff = True
        else:
            user.is_staff = False
        user.save()

    return redirect('curation:user', user_id=user_id)


@check_rules('is_user_superuser')
def change_is_superuser(request, user_id):

    if request.method == "POST":
        user = get_object_or_404(User, pk=user_id)

        is_superuser = request.POST.get('is_superuser', False)
        if is_superuser == 'True':
            user.is_superuser = True
            user.save()

        elif is_superuser == 'False':
            superusers = User.objects.filter(is_superuser=True)

            if len(superusers) > 1:
                user.is_superuser = False
                user.save()
            else:
                message = "This is the only admin user in the system. There have to be at least two adminstrators to remove administrator permissions from a user. "
                messages.add_message(request, messages.ERROR, message)

    return redirect('curation:user', user_id=user_id)


@check_rules('can_update_user_module')
def add_zotero_rule(request, role_id):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = {
        'curation_section': 'users',
        'role': role,
    }

    if request.method == 'POST':
        rule = ZoteroRule.objects.create(role_id=role_id)

    return redirect('curation:role', role_id=role.pk)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def bulk_select_citation(request):
    template = 'curation/bulk_select_citation.html'
    context = {}
    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def bulk_select_authority(request):
    template = 'curation/bulk_select_authority.html'
    context = {}
    return render(request, template, context)

def _get_filtered_queryset(request, object_type='CITATION'):
    pks = request.POST.getlist('queryset')

    filter_params_raw = request.POST.get('filters')
    filter_params = QueryDict(filter_params_raw, mutable=True)
    pks = request.POST.getlist('queryset')
    if pks:
        filter_params['id'] = ','.join(pks)

        # The ``collection_only`` parameter is used in the list view to indicate
        #  that cached parameters should be ignored. That way, when the user
        #  selects a collection in the collection list view they first see all
        #  of the records in that collection. But if specific record IDs are
        #  provided in the POST request, we want to preserve that selection
        #  in the filter; so we remove ``collection_only``.
        if 'collection_only' in filter_params:
            filter_params.pop('collection_only')
    filter_params_raw = filter_params.urlencode()#.encode('utf-8')
    if object_type == 'CITATION':
        _qs = operations.filter_queryset(request.user, Citation.objects.all())
        queryset = CitationFilter(filter_params, queryset=_qs)
    else:
        _qs = operations.filter_queryset(request.user, Authority.objects.all())
        queryset = AuthorityFilter(filter_params, queryset=_qs)
    return queryset, filter_params_raw

def _get_filtered_queryset_authorities(request):
    pks = request.POST.getlist('queryset')

    filter_params_raw = request.POST.get('filters')
    filter_params = QueryDict(filter_params_raw, mutable=True)
    pks = request.POST.getlist('queryset')
    if pks:
        filter_params['id'] = ','.join(pks)

    filter_params_raw = filter_params.urlencode()#.encode('utf-8')

    _qs = operations.filter_queryset(request.user, Authority.objects.all())
    queryset = AuthorityFilter(filter_params, queryset=_qs)

    return queryset, filter_params_raw


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def bulk_action(request):
    """
    User has selected some number of records.

    Selection can be explicit via a list of pks in the ``queryset`` form field,
    or implicit via the ``filters`` from the list view.
    """
    template = 'curation/bulkaction.html'
    object_type = request.POST.get('object_type', 'CITATION')
    queryset, filter_params_raw = _get_filtered_queryset(request, object_type=object_type)
    if isinstance(queryset, CitationFilter) or isinstance(queryset, AuthorityFilter):
        queryset = queryset.qs

    form_class = bulk_action_form_factory(queryset=queryset, object_type=object_type)
    context = {
        'extra_data': '\n'.join(list(form_class.extra_data.values()))
    }

    if request.method != 'POST':
        return HttpResponseRedirect(reverse('curation:citation_list'))

    context.update({'queryset': queryset, 'filters': filter_params_raw})

    if request.GET.get('confirmed', False):
        # Perform the selected action.
        form = form_class(request.POST)
        form.fields['filters'].initial = filter_params_raw
        if form.is_valid():
            tasks = form.apply(request.user, filter_params_raw, extra={'object_type':object_type})
            # task_id = form.apply(queryset.qs, request.user)[0]
            return HttpResponseRedirect(reverse('curation:citation-bulk-action-status') + '?' + '&'.join([urlencode({'task': task}) for task in tasks]))

    else:
        # Prompt to select an action that will be applied to those records.
        form = form_class()
        form.fields['filters'].initial = filter_params_raw


        # form.fields['queryset'].initial = queryset.values_list('id', flat=True)
    context.update({
        'form': form,
        'object_type': object_type,
    })
    return render(request, template, context)






@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def bulk_action_status(request):
    template = 'curation/citations_bulk_status.html'
    context = {}
    task_ids = request.GET.getlist('task')
    tasks = [AsyncTask.objects.get(pk=_pk) for _pk in task_ids]

    context.update({'tasks': tasks})
    return render(request, template, context)


# TODO: refactor around asynchronous tasks.
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def export_citations_status(request):
    template = 'curation/export_status.html'
    context = {
        'exported_type': 'CITATION'
    }
    # target = request.GET.get('target')
    task_id = request.GET.get('task_id')
    task = AsyncTask.objects.get(pk=task_id)
    target = task.value

    download_target = 'https://%s.s3.amazonaws.com/%s' % (settings.AWS_EXPORT_BUCKET_NAME, target)
    context.update({'download_target': download_target, 'task': task})
    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def export_authorities_status(request):
    template = 'curation/export_status.html'
    context = {
        'exported_type': 'AUTHORITY'
    }
    # target = request.GET.get('target')
    task_id = request.GET.get('task_id')
    task = AsyncTask.objects.get(pk=task_id)
    target = task.value

    download_target = 'https://%s.s3.amazonaws.com/%s' % (settings.AWS_EXPORT_BUCKET_NAME, target)
    context.update({'download_target': download_target, 'task': task})
    return render(request, template, context)

def _build_filter_label(filter_params_raw, filter_type='CITATION'):
    if filter_type == 'AUTHORITY':
        current_filter = AuthorityFilter(QueryDict(filter_params_raw, mutable=True))
    else:
        current_filter = CitationFilter(QueryDict(filter_params_raw, mutable=True))
    filter_form = current_filter.form
    filter_data = {}
    if filter_form.is_valid():
        filter_data = filter_form.cleaned_data
    return ', '.join([ '%s: %s' % (key, value) for key, value in list(filter_data.items()) if value ])

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def export_citations(request):
    # TODO: move some of this stuff out to the export module.

    template = 'curation/citations_export.html'
    context = {}
    if request.method != 'POST':
        return HttpResponseRedirect(reverse('curation:citation_list'))

    queryset, filter_params_raw = _get_filtered_queryset(request)
    if isinstance(queryset, CitationFilter):
        queryset = queryset.qs

    if request.GET.get('confirmed', False):
        # The user has selected the desired configuration settings.
        form = ExportCitationsForm(request.POST)
        form.fields['filters'].initial = filter_params_raw

        if form.is_valid():
            # Start the export process.
            tag = slugify(form.cleaned_data.get('export_name', 'export'))
            fields = form.cleaned_data.get('fields')
            export_linked_records = form.cleaned_data.get('export_linked_records')
            export_metadata = form.cleaned_data.get('export_metadata', False)
            use_pipe_delimiter = form.cleaned_data.get('use_pipe_delimiter')

            # TODO: generalize this, so that we are not tied directly to S3.
            _datestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            _out_name = '%s--%s.csv' % (_datestamp, tag)

            s3_path = settings.UPLOAD_IMPORT_PATH + _out_name

            # _compress = form.cleaned_data.get('compress_output', False)
            # if _compress:
            #     s3_path += '.gz'

            # configuration for export
            config = {
                'authority_delimiter': " || " if use_pipe_delimiter else " ",
                'export_metadata': export_metadata
            }

            export_tasks = {
                'EBSCO_CSV': data_tasks.export_to_ebsco_csv,
                'ITEM_COUNT': data_tasks.export_item_counts,
                'SWP_ANALYSIS': data_tasks.export_swp_analysis,
            }

            # We create the AsyncTask object first, so that we can keep it
            #  updated while the task is running.
            task = AsyncTask.objects.create()
            export_task = export_tasks.get(form.cleaned_data.get('export_format', 'CSV'), None)
            if export_task:
                result = export_task.delay(request.user.id, s3_path,
                                                    fields, filter_params_raw,
                                                    task.id, "Citation", export_linked_records, config)
            else:
                result = data_tasks.export_to_csv.delay(request.user.id, s3_path,
                                                    fields, filter_params_raw,
                                                    task.id, "Citation", export_linked_records, config)

            # We can use the AsyncResult's UUID to access this task later, e.g.
            #  to check the return value or task state.
            task.async_uuid = result.id
            task.value = _out_name
            task.label = "Exporting set with filters: " + _build_filter_label(filter_params_raw)
            task.save()

            # Send the user to a status view, which will show the export
            #  progress and a link to the finished export.
            target = reverse('curation:export-citations-status') \
                     + '?' + urlencode({'task_id': task.id})
            return HttpResponseRedirect(target)

    else:       # Display the export configuration form.
        form = ExportCitationsForm()
        form.fields['filters'].initial = filter_params_raw

    context.update({
        'form': form,
        'queryset': queryset,
    })

    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def export_authorities(request):
    # TODO: move some of this stuff out to the export module.

    template = 'curation/authorities_export.html'
    context = {}
    if request.method != 'POST':
        return HttpResponseRedirect(reverse('curation:authority_list'))

    queryset, filter_params_raw = _get_filtered_queryset_authorities(request)

    if isinstance(queryset, AuthorityFilter):
        queryset = queryset.qs

    if request.GET.get('confirmed', False):
        # The user has selected the desired configuration settings.
        form = ExportAuthorityForm(request.POST)
        form.fields['filters'].initial = filter_params_raw

        if form.is_valid():
            # Start the export process.
            tag = slugify(form.cleaned_data.get('export_name', 'export'))
            fields = form.cleaned_data.get('fields')
            export_metadata = form.cleaned_data.get('export_metadata', False)

            # TODO: generalize this, so that we are not tied directly to S3.
            _datestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            _out_name = '%s--%s.csv' % (_datestamp, tag)
            # _compress = form.cleaned_data.get('compress_output', False)
            s3_path = 's3://%s:%s@%s/%s' % (settings.AWS_ACCESS_KEY_ID,
                                            settings.AWS_SECRET_ACCESS_KEY,
                                            settings.AWS_EXPORT_BUCKET_NAME,
                                            _out_name)

            # if _compress:
            #     s3_path += '.gz'

            # configuration for export
            config = {
                'export_metadata': export_metadata,
            }

            # We create the AsyncTask object first, so that we can keep it
            #  updated while the task is running.
            task = AsyncTask.objects.create()
            result = data_tasks.export_to_csv.delay(request.user.id, s3_path,
                                                    fields, filter_params_raw,
                                                    task.id, 'Authority', config=config)

            # We can use the AsyncResult's UUID to access this task later, e.g.
            #  to check the return value or task state.
            task.async_uuid = result.id
            task.value = _out_name
            task.label = "Exporting set with filters: " + _build_filter_label(filter_params_raw, 'AUTHORITY')
            task.save()

            # Send the user to a status view, which will show the export
            #  progress and a link to the finished export.
            target = reverse('curation:export-authorities-status') \
                     + '?' + urlencode({'task_id': task.id})
            return HttpResponseRedirect(target)

    else:       # Display the export configuration form.
        form = ExportAuthorityForm()
        form.fields['filters'].initial = filter_params_raw

    context.update({
        'form': form,
        'queryset': queryset,
    })

    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def collections(request):
    """
    List :class:`.Collection` instances.
    """
    from curation.filters import CitationCollectionFilter
    return _list_collections(request, CitationCollectionFilter, CitationCollection, 'CITATION', 'curation/collection_list.html')

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def authority_collections(request):
    """
    List :class:`.AuthorityCollection` instances.
    """
    from curation.filters import AuthorityCollectionFilter
    return _list_collections(request, AuthorityCollectionFilter, AuthorityCollection, 'AUTHORITY', 'curation/collection_list.html')

def _list_collections(request, collection_filter_class, collection_class, type, template):
    # ISISCB-1050: reverse sort order of collections (newest first)
    collections = collection_class.objects.all().order_by('-created')

    filtered_objects = collection_filter_class(request.GET, queryset=collections)
    paginator = Paginator(filtered_objects.qs, PAGE_SIZE)

    raw_params = request.GET.urlencode()
    filter_params = QueryDict(raw_params, mutable=True)
    current_page = filter_params.get('page', 1)
    if not current_page:
        current_page = 1
    current_page = int(current_page)
    page = paginator.page(current_page)
    paginated_objects = list(page)

    context = {
        'filter_list': paginated_objects,
        'type': type,
        'page': page,
        'paginator': paginator,
        'current_offset': (current_page - 1) * PAGE_SIZE,
        'current_page': current_page,
        'objects': filtered_objects,
    }
    return render(request, template, context)



@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def create_citation_collection(request):
    template = 'curation/citation_collection_create.html'
    context = {}
    if request.method == 'POST':
        queryset, filter_params_raw = _get_filtered_queryset(request)
        if isinstance(queryset, CitationFilter):
            queryset = queryset.qs
        if request.GET.get('confirmed', False):
            form = CitationCollectionForm(request.POST)
            form.fields['filters'].initial = filter_params_raw
            if form.is_valid():
                instance = form.save(commit=False)
                instance.createdBy = request.user
                instance.save()
                instance.citations.add(*queryset)

                # TODO: add filter paramter to select collection.
                return HttpResponseRedirect(reverse('curation:citation_list') + '?in_collections=%i' % instance.id)
        else:
            form = CitationCollectionForm()
            form.fields['filters'].initial = filter_params_raw

        context.update({
            'form': form,
            'queryset': queryset,
        })

    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def create_authority_collection(request):
    template = 'curation/authority_collection_create.html'
    context = {}
    if request.method == 'POST':
        queryset, filter_params_raw = _get_filtered_queryset(request, 'AUTHORITY')
        if isinstance(queryset, AuthorityFilter):
            queryset = queryset.qs
        if request.GET.get('confirmed', False):
            form = AuthorityCollectionForm(request.POST)
            form.fields['filters'].initial = filter_params_raw
            if form.is_valid():
                instance = form.save(commit=False)
                instance.createdBy = request.user
                instance.save()
                instance.authorities.add(*queryset)

                # TODO: add filter paramter to select collection.
                return HttpResponseRedirect(reverse('curation:authority_list') + '?in_collections=%i' % instance.id)
        else:
            form = AuthorityCollectionForm()
            form.fields['filters'].initial = filter_params_raw

        context.update({
            'form': form,
            'queryset': queryset,
        })

    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def add_citation_collection(request):
    template = 'curation/citation_collection_add.html'
    context = {}

    if request.method == 'POST':
        queryset, filter_params_raw = _get_filtered_queryset(request)
        if isinstance(queryset, CitationFilter):
            queryset = queryset.qs
        if request.GET.get('confirmed', False):
            form = SelectCitationCollectionForm(request.POST)
            form.fields['filters'].initial = filter_params_raw
            if form.is_valid():
                collection = form.cleaned_data['collection']
                collection.citations.add(*queryset)

                # TODO: add filter paramter to select collection.
                return HttpResponseRedirect(reverse('curation:citation_list') + '?in_collections=%i' % collection.id)
        else:
            form = SelectCitationCollectionForm()
            form.fields['filters'].initial = filter_params_raw

        context.update({
            'form': form,
            'queryset': queryset,
        })

    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def add_authority_collection(request):
    template = 'curation/authority_collection_add.html'
    context = {}

    if request.method == 'POST':
        queryset, filter_params_raw = _get_filtered_queryset(request, 'AUTHORITY')
        if isinstance(queryset, AuthorityFilter):
            queryset = queryset.qs
        if request.GET.get('confirmed', False):
            form = SelectAuthorityCollectionForm(request.POST)
            form.fields['filters'].initial = filter_params_raw
            if form.is_valid():
                collection = form.cleaned_data['collection']
                collection.authorities.add(*queryset)

                # TODO: add filter paramter to select collection.
                return HttpResponseRedirect(reverse('curation:authority_list') + '?in_collections=%i' % collection.id)
        else:
            form = SelectAuthorityCollectionForm()
            form.fields['filters'].initial = filter_params_raw

        context.update({
            'form': form,
            'queryset': queryset,
        })

    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_view_user_module')
def users(request, user_id=None):
    from curation.filters import UserFilter
    context = {
        'curation_section': 'users',
    }
    template = 'curation/users.html'
    users =  User.objects.all()
    filterset = UserFilter(request.GET, queryset=users)

    paginator = Paginator(filterset.qs, PAGE_SIZE)
    current_page = request.GET.get('page', 1)
    if not current_page:
        current_page = 1
    current_page = int(current_page)
    page = paginator.page(current_page)
    paginated_objects = list(page)

    context.update({
        'objects': paginated_objects,
        'filterset': filterset,
        'paginator': paginator,
        'page': page,
        'current_page': current_page,
    })
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_view_user_module')
def user(request, user_id):
    selected_user = get_object_or_404(User, pk=user_id)


    context = {
        'curation_section': 'users',
        'selected_user': selected_user,
    }
    template = 'curation/user.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def add_role(request, user_id=None):
    context = {
        'curation_section': 'users',
    }

    if request.method == 'GET':
        template = 'curation/add_role.html'
        form = RoleForm()
        context.update({
            'form': form,
        })
    elif request.method == 'POST':
        form = RoleForm(request.POST)

        if form.is_valid():
            role = form.save()

            return redirect('curation:roles')
        else:
            template = 'curation/add_role.html'
            context.update({
                'form': form,
            })
    else:
        return redirect('curation:roles')

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def remove_role(request, user_id, role_id):
    role = get_object_or_404(IsisCBRole, pk=role_id)
    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        role.users.remove(user)

    return redirect('curation:user', user_id=user.pk)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def delete_role(request, role_id):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    if request.method == 'POST':
        if role.users.all():
            usernames = [user.username for user in role.users.all()]
            message = "Only roles that are not assigned to any user can be deleted. This role has the following users assigned: " + ", ".join(usernames) + "."
            messages.add_message(request, messages.ERROR, message)
        else:
            role.delete()

    return redirect('curation:roles')


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_view_user_module')
def role(request, role_id, user_id=None):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    template = 'curation/role.html'
    context = {
        'curation_section': 'users',
        'role': role,
    }

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_view_user_module')
def roles(request):
    roles = IsisCBRole.objects.all()

    template = 'curation/roles.html'
    context = {
        'curation_section': 'users',
        'roles': roles,
    }

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def add_dataset_rule(request, role_id, user_id=None):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = {
        'curation_section': 'users',
        'role': role,
    }

    if request.method == 'GET':
        template = 'curation/add_rule.html'
        form = DatasetRuleForm(initial = { 'role': role })
        header_template = get_template('curation/rule_dataset_header.html').render(context)
        context.update({
            'form': form,
            'header': header_template
        })
    elif request.method == 'POST':
        form = DatasetRuleForm(request.POST)

        if form.is_valid():
            rule = form.save()
            rule.role = role
            rule.save()

            return redirect('curation:role', role_id=role.pk)
        else:
            template = 'curation/add_rule.html'
            header_template = get_template('curation/rule_dataset_header.html').render(context)

            context.update({
                'form': form,
                'header': header_template,
            })

        return redirect('curation:role', role_id=role.pk)

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def add_crud_rule(request, role_id, user_id=None):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = {
        'curation_section': 'users',
        'role': role,
    }

    if request.method == 'GET':
        template = 'curation/add_rule.html'
        header_template = get_template('curation/rule_crud_header.html').render(context)

        form = CRUDRuleForm(initial = { 'role': role })
        context.update({
            'form': form,
            'header': header_template,
        })
    elif request.method == 'POST':
        form = CRUDRuleForm(request.POST)

        if form.is_valid():
            rule = form.save()
            rule.role = role
            rule.save()

            return redirect('curation:role', role_id=role.pk)
        else:
            template = 'curation/add_rule.html'
            header_template = get_template('curation/rule_crud_header.html').render(context)

            context.update({
                'form': form,
                'header_template': header_template,
            })

        return redirect('curation:role', role_id=role.pk)

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def add_field_rule(request, role_id, user_id=None, object_type=AccessRule.CITATION):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = {
        'curation_section': 'users',
        'role': role,
    }

    if request.method == 'GET':
        template = 'curation/add_rule.html'
        if object_type == AccessRule.CITATION:
            form = FieldRuleCitationForm(initial = { 'role': role, 'object_type': object_type})
            header_template = 'curation/rule_field_citation_header.html'
        else:
            form = FieldRuleAuthorityForm(initial = { 'role': role, 'object_type': object_type})
            header_template = 'curation/rule_field_authority_header.html'

        header_template = get_template(header_template).render(context)
        context.update({
            'form': form,
            'header': header_template
        })
    elif request.method == 'POST':
        if object_type == AccessRule.CITATION:
            form = FieldRuleCitationForm(request.POST)
            header_template = 'curation/rule_field_citation_header.html'
        else:
            form = FieldRuleAuthorityForm(request.POST)
            header_template = 'curation/rule_field_authority_header.html'

        if form.is_valid():
            rule = form.save()
            rule.object_type = object_type
            rule.role = role
            rule.save()

            return redirect('curation:role', role_id=role.pk)
        else:
            template = 'curation/add_rule.html'
            header_template = get_template(header_template).render(context)

            context.update({
                'form': form,
                'header': header_template,
            })

        return redirect('curation:role', role_id=role.pk)

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def add_user_module_rule(request, role_id):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = {
        'curation_section': 'users',
        'role': role,
    }

    if request.method == 'GET':
        template = 'curation/add_rule.html'
        form = UserModuleRuleForm()

        header_template = get_template('curation/rule_user_module_header.html').render(context)
        context.update({
            'form': form,
            'header': header_template
        })
    elif request.method == 'POST':
        form = UserModuleRuleForm(request.POST)

        if form.is_valid():
            rule = form.save()
            rule.role = role
            rule.save()

            return redirect('curation:role', role_id=role.pk)
        else:
            template = 'curation/add_rule.html'
            header_template = get_template('curation/rule_user_module_header.html').render(context)

            context.update({
                'form': form,
                'header_template': header_template,
            })

        return redirect('curation:role', role_id=role.pk)

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def add_role_to_user(request, user_edit_id, user_id=None):
    user = get_object_or_404(User, pk=user_edit_id)

    context = {
        'curation_section': 'users',
    }

    if request.method == 'GET':
        template = 'curation/add_role_to_user.html'
        form = AddRoleForm(initial = { 'users': user })
        context.update({
            'form': form,
        })
    elif request.method == 'POST':
        form = AddRoleForm(request.POST)

        if form.is_valid():
            role_id = form.cleaned_data['role']
            role = get_object_or_404(IsisCBRole, pk=role_id)
            role.users.add(user)
            role.save()

            if request.GET.get('from_user', False):
                return redirect('curation:user', user.pk)

            return redirect('curation:user_list')

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def remove_rule(request, role_id, rule_id):
    role = get_object_or_404(IsisCBRole, pk=role_id)
    rule = get_object_or_404(AccessRule, pk=rule_id)

    if request.method == 'POST':
        rule.delete()

    return redirect('curation:role', role_id=role.pk)
