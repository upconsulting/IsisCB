from __future__ import absolute_import

from django.template import RequestContext, loader
from django.contrib.admin.views.decorators import staff_member_required, user_passes_test
from django.contrib import messages

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse #, HttpResponseForbidden, Http404, , JsonResponse
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.core.cache import caches
from django.contrib.auth.models import User
from django.shortcuts import redirect

from rules.contrib.views import permission_required, objectgetter
from .rules import is_accessible_by_dataset
from django.forms import modelform_factory, formset_factory


from isisdata.models import *
from curation.filters import *
from curation.forms import *
from curation.contrib.views import check_rules

import iso8601
import rules
from itertools import chain


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

@staff_member_required
def dashboard(request):
    """
    """
    template = loader.get_template('curation/dashboard.html')
    context = RequestContext(request, {

    })
    return HttpResponse(template.render(context))

@staff_member_required
def datasets(request):
    """
    """
    template = loader.get_template('curation/dashboard.html')
    context = RequestContext(request, {
        'curation_section':'datasets',
    })
    return HttpResponse(template.render(context))

@staff_member_required
#@check_rules('can_create_record')
def create_citation(request):

    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
    })

    template = loader.get_template('curation/citation_create_view.html')

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
            return HttpResponseRedirect(reverse('curate_citation', args=(citation.id,)))
        else:
            context.update({
                'form' : form,
                'partdetails_form': partdetails_form,
            })

    return HttpResponse(template.render(context))

@staff_member_required
#@check_rules('can_create_record')
def create_authority(request):
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
    })

    template = loader.get_template('curation/authority_create_view.html')
    person_form = None
    if request.method == 'GET':
        form = AuthorityForm(user=request.user, prefix='authority')

        context.update({
            'form': form,
        })
    elif request.method == 'POST':
        authority = Authority()
        if request.POST.get('authority-type_controlled', '') == Authority.PERSON:
            authority = Person()
            person_form = PersonForm(request.user, None, request.POST, instance=authority)

        form = AuthorityForm(request.user, request.POST, prefix='authority', instance=authority)
        if form.is_valid() and (person_form is None or person_form.is_valid()):
            if person_form:
                person_form.save()

            form.cleaned_data['public'] = False
            form.cleaned_data['record_status_value'] = CuratedMixin.INACTIVE
            authority = form.save()

            return HttpResponseRedirect(reverse('curate_authority', args=(authority.id,)))
        else:
            context.update({
                'form' : form,
            })
    return HttpResponse(template.render(context))

# TODO this method needs to be logged down!
@staff_member_required
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


@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def create_ccrelation_for_citation(request, citation_id):
    citation = get_object_or_404(Citation, pk=citation_id)

    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
    })
    if request.method == 'GET':
        ccrelation = CCRelation()
        initial={}
        if citation.type_controlled == Citation.CHAPTER:
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
            return HttpResponseRedirect(reverse('curate_citation', args=(citation.id,)) + '?tab=ccrelations')

    context.update({
        'form': form,
    })
    template = loader.get_template('curation/citation_ccrelation_changeview.html')
    return HttpResponse(template.render(context))


@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def ccrelation_for_citation(request, citation_id, ccrelation_id=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    ccrelation = None if not ccrelation_id else get_object_or_404(CCRelation, pk=ccrelation_id)

    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'ccrelation': ccrelation,
    })
    if request.method == 'GET':
        if ccrelation:
            form = CCRelationForm(instance=ccrelation, prefix='ccrelation')
        else:
            form = CCRelationForm(prefix='ccrelation', initial={'subject': citation.id})

    elif request.method == 'POST':
        form = CCRelationForm(request.POST, instance=ccrelation, prefix='ccrelation')
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('curate_citation', args=(citation.id,)) + '?tab=ccrelations')

    context.update({
        'form': form,
    })
    template = loader.get_template('curation/citation_ccrelation_changeview.html')
    return HttpResponse(template.render(context))


@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def create_acrelation_for_authority(request, authority_id):
    authority = get_object_or_404(Authority, pk=authority_id)

    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,

    })
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
            return HttpResponseRedirect(reverse('curate_authority', args=(authority.id,)) + '?tab=acrelations')

    context.update({
        'form': form,
    })
    template = loader.get_template('curation/authority_acrelation_changeview.html')
    return HttpResponse(template.render(context))


@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def acrelation_for_authority(request, authority_id, acrelation_id):
    authority = get_object_or_404(Authority, pk=authority_id)
    acrelation = get_object_or_404(ACRelation, pk=acrelation_id)

    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'acrelation': acrelation,
    })
    if request.method == 'GET':
        form = ACRelationForm(instance=acrelation, prefix='acrelation')

    elif request.method == 'POST':
        form = ACRelationForm(request.POST, instance=acrelation, prefix='acrelation')
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('curate_authority', args=(authority.id,)) + '?tab=acrelations')

    context.update({
        'form': form,
    })
    template = loader.get_template('curation/authority_acrelation_changeview.html')
    return HttpResponse(template.render(context))


@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def create_acrelation_for_citation(request, citation_id):
    citation = get_object_or_404(Citation, pk=citation_id)

    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
    })
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
            return HttpResponseRedirect(reverse('curate_citation', args=(citation.id,)) + '?tab=acrelations')

    context.update({
        'form': form,
    })
    template = loader.get_template('curation/citation_acrelation_changeview.html')
    return HttpResponse(template.render(context))


@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def acrelation_for_citation(request, citation_id, acrelation_id=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    acrelation = None if not acrelation_id else get_object_or_404(ACRelation, pk=acrelation_id)

    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'acrelation': acrelation,
    })
    if request.method == 'GET':
        form = ACRelationForm(instance=acrelation, prefix='acrelation')

    elif request.method == 'POST':
        form = ACRelationForm(request.POST, instance=acrelation, prefix='acrelation')
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('curate_citation', args=(citation.id,)) + '?tab=acrelations')

    context.update({
        'form': form,
    })
    template = loader.get_template('curation/citation_acrelation_changeview.html')
    return HttpResponse(template.render(context))


@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def delete_attribute_for_citation(request, citation_id, attribute_id, format=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    attribute = get_object_or_404(Attribute, pk=attribute_id)
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'attribute': attribute,
    })
    if request.GET.get('confirm', False):
        attribute.delete()
        if format == 'json':
            return JsonResponse({'result': True})
        return HttpResponseRedirect(reverse('curate_citation', args=(citation.id,)) + '?tab=attributes')
    template = loader.get_template('curation/citation_attribute_delete.html')
    return HttpResponse(template.render(context))

@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def delete_linkeddata_for_citation(request, citation_id, linkeddata_id, format=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    linkeddata = get_object_or_404(LinkedData, pk=linkeddata_id)
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'linkeddata': linkeddata,
    })

    if request.GET.get('confirm', False):
        linkeddata.delete()

        if format == 'json':
            return JsonResponse({'result': True})
        return HttpResponseRedirect(reverse('curate_citation', args=(citation.id,)) + '?tab=linkeddata')
    template = loader.get_template('curation/citation_linkeddata_delete.html')
    return HttpResponse(template.render(context))

@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def delete_linkeddata_for_authority(request, authority_id, linkeddata_id, format=None):
    authority = get_object_or_404(Authority, pk=authority_id)
    linkeddata = get_object_or_404(LinkedData, pk=linkeddata_id)
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'linkeddata': linkeddata,
    })

    if request.GET.get('confirm', False):
        linkeddata.delete()

        if format == 'json':
            return JsonResponse({'result': True})
        return HttpResponseRedirect(reverse('curate_authority', args=(authority.id,)) + '?tab=linkeddata')
    template = loader.get_template('curation/authority_linkeddata_delete.html')
    return HttpResponse(template.render(context))

@staff_member_required
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


@staff_member_required
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


@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def delete_ccrelation_for_citation(request, citation_id, ccrelation_id, format=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    ccrelation = get_object_or_404(CCRelation, pk=ccrelation_id)
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'ccrelation': ccrelation,
    })
    if request.GET.get('confirm', False):
        ccrelation.delete()
        if format == 'json':
            return JsonResponse({'result': True})
        return HttpResponseRedirect(reverse('curate_citation', args=(citation.id,)) + '?tab=ccrelations')
    template = loader.get_template('curation/citation_ccrelation_delete.html')
    return HttpResponse(template.render(context))


@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def delete_acrelation_for_citation(request, citation_id, acrelation_id, format=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    acrelation = get_object_or_404(ACRelation, pk=acrelation_id)
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'acrelation': acrelation,
    })
    if request.GET.get('confirm', False):
        acrelation.delete()
        if format == 'json':
            return JsonResponse({'result': True})
        return HttpResponseRedirect(reverse('curate_citation', args=(citation.id,)) + '?tab=acrelations')
    template = loader.get_template('curation/citation_acrelation_delete.html')
    return HttpResponse(template.render(context))


@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def delete_acrelation_for_authority(request, authority_id, acrelation_id, format=None):
    authority = get_object_or_404(Authority, pk=authority_id)
    acrelation = get_object_or_404(ACRelation, pk=acrelation_id)
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'acrelation': acrelation,
    })
    if request.GET.get('confirm', False):
        acrelation.delete()
        if format == 'json':
            return JsonResponse({'result': True})
        return HttpResponseRedirect(reverse('curate_authority', args=(authority.id,)) + '?tab=acrelations')
    template = loader.get_template('curation/authority_acrelation_delete.html')
    return HttpResponse(template.render(context))


@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def delete_attribute_for_authority(request, authority_id, attribute_id, format=None):
    authority = get_object_or_404(Authority, pk=authority_id)
    attribute = get_object_or_404(Attribute, pk=attribute_id)
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'attribute': attribute,
    })
    if request.GET.get('confirm', False):
        attribute.delete()
        if format == 'json':
            return JsonResponse({'result': True})
        return HttpResponseRedirect(reverse('curate_authority', args=(authority.id,)) + '?tab=attributes')
    template = loader.get_template('curation/authority_attribute_delete.html')
    return HttpResponse(template.render(context))

@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def linkeddata_for_citation(request, citation_id, linkeddata_id=None):

    template = loader.get_template('curation/citation_linkeddata_changeview.html')
    citation = get_object_or_404(Citation, pk=citation_id)
    linkeddata = None

    if linkeddata_id:
        linkeddata = get_object_or_404(LinkedData, pk=linkeddata_id)

    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'linkeddata': linkeddata,
    })

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

            return HttpResponseRedirect(reverse('curate_citation', args=(citation.id,)) + '?tab=linkeddata')
        else:
            pass
    else:
        redirect('curate_citation', citation_id)

    context.update({
        'linkeddata_form': linkeddata_form,
    })
    return HttpResponse(template.render(context))

@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def linkeddata_for_authority(request, authority_id, linkeddata_id=None):

    template = loader.get_template('curation/authority_linkeddata_changeview.html')
    authority = get_object_or_404(Authority, pk=authority_id)
    linkeddata = None

    if linkeddata_id:
        linkeddata = get_object_or_404(LinkedData, pk=linkeddata_id)

    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': authority,
        'linkeddata': linkeddata,
    })

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

            return HttpResponseRedirect(reverse('curate_authority', args=(authority.id,)) + '?tab=linkeddata')
        else:
            pass
    else:
        redirect('curate_authority', authority_id)

    context.update({
        'linkeddata_form': linkeddata_form,
    })
    return HttpResponse(template.render(context))

@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def attribute_for_citation(request, citation_id, attribute_id=None):

    template = loader.get_template('curation/citation_attribute_changeview.html')
    citation = get_object_or_404(Citation, pk=citation_id)
    attribute, value, value_form, value_form_class = None, None, None, None

    value_forms = {}
    for at in AttributeType.objects.all():
        value_class = at.value_content_type.model_class()
        if value_class is ISODateValue:
            value_forms[at.id] = ISODateValueForm
        else:
            value_forms[at.id] = modelform_factory(value_class,
                                    exclude=('attribute', 'child_class'))

    if attribute_id:
        attribute = get_object_or_404(Attribute, pk=attribute_id)
        if hasattr(attribute, 'value'):
            value = attribute.value.get_child_class()
            value_form_class = value_forms[attribute.type_controlled.id]

    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'attribute': attribute,
        'value': value,
    })

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

            attribute_form.instance.source = citation
            attribute_form.save()
            value_form.instance.attribute = attribute_form.instance
            value_form.save()

            return HttpResponseRedirect(reverse('curate_citation', args=(citation.id,)) + '?tab=attributes')
        else:
            pass

    context.update({
        'attribute_form': attribute_form,
        'value_form': value_form,
        'value_forms': [(i, f(prefix='value')) for i, f in value_forms.iteritems()],
    })
    return HttpResponse(template.render(context))


@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def attribute_for_authority(request, authority_id, attribute_id=None):

    template = loader.get_template('curation/authority_attribute_changeview.html')
    authority = get_object_or_404(Authority, pk=authority_id)
    attribute, value, value_form, value_form_class = None, None, None, None

    value_forms = {}
    for at in AttributeType.objects.all():
        value_class = at.value_content_type.model_class()
        if value_class is ISODateValue:
            value_forms[at.id] = ISODateValueForm
        else:
            value_forms[at.id] = modelform_factory(value_class,
                                    exclude=('attribute', 'child_class'))

    if attribute_id:
        attribute = get_object_or_404(Attribute, pk=attribute_id)
        if hasattr(attribute, 'value'):
            value = attribute.value.get_child_class()
            value_form_class = value_forms[attribute.type_controlled.id]

    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'attribute': attribute,
        'value': value,
    })

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
            attribute_form.save()
            value_form.instance.attribute = attribute_form.instance
            value_form.save()

            return HttpResponseRedirect(reverse('curate_authority', args=(authority.id,)) + '?tab=attributes')
        else:
            pass

    context.update({
        'attribute_form': attribute_form,
        'value_form': value_form,
        'value_forms': [(i, f(prefix='value')) for i, f in value_forms.iteritems()],
    })
    return HttpResponse(template.render(context))


@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def citation(request, citation_id):
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
    })

    citation = get_object_or_404(Citation, pk=citation_id)

    user_cache = caches['default']
    result_list = user_cache.get('result_list', None)
    request_params = user_cache.get('request_params', "")

    if request_params:
        context.update({
            'request_params': request_params,
        })

    if result_list:
        index = result_list.index(citation)
        next = result_list[index+1] if len(result_list) > index+1 else None
        previous = result_list[index-1] if index > 0 else None

        context.update({
            'next': next,
            'previous': previous,
        })

    if citation.type_controlled == Citation.BOOK:
        template = loader.get_template('curation/citation_change_view_book.html')
    elif citation.type_controlled in (Citation.REVIEW, Citation.ESSAY_REVIEW):
        template = loader.get_template('curation/citation_change_view_review.html')
    elif citation.type_controlled == Citation.CHAPTER:
        template = loader.get_template('curation/citation_change_view_chapter.html')
    elif citation.type_controlled == Citation.ARTICLE:
        template = loader.get_template('curation/citation_change_view_article.html')
    elif citation.type_controlled == Citation.THESIS:
        template = loader.get_template('curation/citation_change_view_thesis.html')
    else:
        template = loader.get_template('curation/citation_change_view.html')
    partdetails_form = None
    context.update({'tab': request.GET.get('tab', None)})
    if request.method == 'GET':
        form = CitationForm(user=request.user, instance=citation)
        context.update({
            'form': form,
            'instance': citation,
        })
        if citation.type_controlled in [Citation.ARTICLE, Citation.BOOK, Citation.REVIEW, Citation.CHAPTER, Citation.THESIS]:
            part_details = getattr(citation, 'part_details', None)
            if not part_details:
                part_details = PartDetails.objects.create()
                citation.part_details = part_details
                citation.save()

            partdetails_form = PartDetailsForm(request.user, citation_id, instance=part_details, prefix='partdetails')
            context.update({
                'partdetails_form': partdetails_form,
            })
    elif request.method == 'POST':
        form = CitationForm(request.user, request.POST, instance=citation)
        if citation.type_controlled in [Citation.ARTICLE, Citation.BOOK, Citation.REVIEW, Citation.CHAPTER, Citation.THESIS] and hasattr(citation, 'part_details'):
            partdetails_form = PartDetailsForm(request.user, citation_id, request.POST, prefix='partdetails', instance=citation.part_details)
        if form.is_valid() and (partdetails_form is None or partdetails_form.is_valid()):
            form.save()
            if partdetails_form:
                partdetails_form.save()

            return HttpResponseRedirect(reverse('curate_citation', args=(citation.id,)))

        context.update({
            'form': form,
            'instance': citation,
            'partdetails_form': partdetails_form,
        })

    return HttpResponse(template.render(context))

@staff_member_required
def citations(request):
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
    })

    template = loader.get_template('curation/citation_list_view.html')

    queryset = filter_queryset(request.user, Citation.objects.all())
    filtered_objects = CitationFilter(request.GET, queryset=queryset)

    filters_active = request.GET.get('filters', False)
    filters_active = filters_active or len([v for k, v in request.GET.iteritems() if len(v) > 0 and k != 'page']) > 0


    # 'search_results_cache' is the database cache
    #  (see production_settings.py).
    user_cache = caches['default']
    user_cache.set('result_list', list(filtered_objects.qs.all()))
    user_cache.set('request_params', request.META['QUERY_STRING'])

    context.update({
        'objects': filtered_objects,
        'filters_active': filters_active,
    })

    return HttpResponse(template.render(context))

def filter_queryset(user, queryset):
    roles = IsisCBRole.objects.filter(users__pk=user.pk)

    datasets = []
    excluded_datasets = []
    can_view_all = False

    if user.is_superuser:
        can_view_all = True
    else:
        for role in roles:
            # if there are dataset limitations in role
            if role.dataset_rules:
                crud_actions = [rule.crud_action for rule in role.crud_rules]
                datasets_in_role = [rule.dataset for rule in role.dataset_rules]
                # if the crud rules allow viewing records in datasets add them to included datasets
                if CRUDRule.VIEW in crud_actions:
                    datasets += datasets_in_role
                # otherwise exclude datasets
                else:
                    excluded_datasets += datasets_in_role
            # if there are no dataset limitations
            else:
                crud_actions = [rule.crud_action for rule in role.crud_rules]
                if CRUDRule.VIEW in crud_actions:
                    can_view_all = True

    if excluded_datasets:
        queryset = queryset.exclude(belongs_to__in=excluded_datasets)
    if not can_view_all:
        queryset = queryset.filter(belongs_to__in=datasets)

    return queryset

@staff_member_required
def authorities(request):
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
    })

    template = loader.get_template('curation/authority_list_view.html')
    queryset = filter_queryset(request.user, Authority.objects.all())
    filtered_objects = AuthorityFilter(request.GET, queryset=queryset)
    filters_active = request.GET.get('filters', False)
    filters_active = filters_active or len([v for k, v in request.GET.iteritems() if len(v) > 0 and k != 'page']) > 0
    context.update({
        'objects': filtered_objects,
        'filters_active': filters_active
    })

    return HttpResponse(template.render(context))

@staff_member_required
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def authority(request, authority_id):
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
    })

    context.update({'tab': request.GET.get('tab', None)})
    authority = get_object_or_404(Authority, pk=authority_id)
    template = loader.get_template('curation/authority_change_view.html')
    person_form = None
    if request.method == 'GET':
        if authority.type_controlled == Authority.PERSON and hasattr(Authority, 'person'):
            person_form = PersonForm(request.user, authority_id, instance=authority.person)

        form = AuthorityForm(request.user, instance=authority, prefix='authority')
        context.update({
            'form': form,
            'instance': authority,
            'person_form': person_form,
        })


    elif request.method == 'POST':
        if authority.type_controlled == Authority.PERSON and hasattr(Authority, 'person'):
            person_form = PersonForm(request.user, authority_id, request.POST, instance=authority.person)

        form = AuthorityForm(request.user, request.POST, instance=authority, prefix='authority')
        if form.is_valid() and (person_form is None or person_form.is_valid()):
            if person_form:
                person_form.save()

            form.save()

            return HttpResponseRedirect(reverse('curate_authority', args=[authority.id,]))

        context.update({
            'form': form,
            'person_form': person_form,
            'instance': authority,
            # 'partdetails_form': partdetails_form,
        })

    return HttpResponse(template.render(context))


@staff_member_required
def quick_and_dirty_language_search(request):
    q = request.GET.get('q', None)
    if not q or len(q) < 3:
        return JsonResponse({'results': []})
    queryset = Language.objects.filter(name__istartswith=q)
    results = [{
        'id': language.id,
        'name': language.name,
        'public': True,
    } for language in queryset[:20]]
    return JsonResponse({'results': results})


@staff_member_required
def quick_and_dirty_authority_search(request):
    q = request.GET.get('q', None)
    tc = request.GET.get('type', None)
    N = int(request.GET.get('max', 10))
    if not q or len(q) < 3:
        return JsonResponse({'results': []})

    queryset = Authority.objects.all()
    queryset_sw = Authority.objects.all()
    if tc:
        queryset = queryset.filter(type_controlled=tc.upper())
        queryset_sw = queryset_sw.filter(type_controlled=tc.upper())

    query_parts = q.split()
    for part in query_parts:
        queryset = queryset.filter(name__icontains=part)
    queryset_sw = queryset_sw.filter(name__istartswith=q)
    results = []
    for i, obj in enumerate(chain(queryset_sw, queryset.order_by('name'))):
        if i == N:
            break

        results.append({
            'id': obj.id,
            'type': obj.get_type_controlled_display(),
            'name': obj.name,
            'description': obj.description,
            'datestring': _get_datestring_for_authority(obj),
            'url': reverse("curate_authority", args=(obj.id,)),
            'public': obj.public,
        })
    return JsonResponse({'results': results})


@staff_member_required
def dataset(request, dataset_id=None):
    return HttpResponse('')


@staff_member_required
@check_rules('can_view_user_module')
def users(request, user_id=None):
    context = RequestContext(request, {
        'curation_section': 'users',
    })
    template = loader.get_template('curation/users.html')
    users =  User.objects.all()
    context.update({
        'objects': users,
    })
    return HttpResponse(template.render(context))

@staff_member_required
@check_rules('can_view_user_module')
def user(request, user_id):
    selected_user = get_object_or_404(User, pk=user_id)


    context = RequestContext(request, {
        'curation_section': 'users',
        'selected_user': selected_user,
    })
    template = loader.get_template('curation/user.html')
    return HttpResponse(template.render(context))

@staff_member_required
@check_rules('can_update_user_module')
def add_role(request, user_id=None):
    context = RequestContext(request, {
        'curation_section': 'users',
    })

    if request.method == 'GET':
        template = loader.get_template('curation/add_role.html')
        form = RoleForm()
        context.update({
            'form': form,
        })
    elif request.method == 'POST':
        form = RoleForm(request.POST)

        if form.is_valid():
            role = form.save()

            return redirect('roles')
        else:
            template = loader.get_template('curation/add_role.html')
            context.update({
                'form': form,
            })
    else:
        return redirect('roles')

    return HttpResponse(template.render(context))

@staff_member_required
@check_rules('can_update_user_module')
def remove_role(request, user_id, role_id):
    role = get_object_or_404(IsisCBRole, pk=role_id)
    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        role.users.remove(user)

    return redirect('user', user_id=user.pk)

@staff_member_required
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

    return redirect('roles')

@staff_member_required
@check_rules('can_view_user_module')
def role(request, role_id, user_id=None):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    template = loader.get_template('curation/role.html')
    context = RequestContext(request, {
        'curation_section': 'users',
        'role': role,
    })

    return HttpResponse(template.render(context))

@staff_member_required
@check_rules('can_view_user_module')
def roles(request):
    roles = IsisCBRole.objects.all()

    template = loader.get_template('curation/roles.html')
    context = RequestContext(request, {
        'curation_section': 'users',
        'roles': roles,
    })

    return HttpResponse(template.render(context))

@staff_member_required
@check_rules('can_update_user_module')
def add_dataset_rule(request, role_id, user_id=None):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = RequestContext(request, {
        'curation_section': 'users',
        'role': role,
    })

    if request.method == 'GET':
        template = loader.get_template('curation/add_rule.html')
        form = DatasetRuleForm(initial = { 'role': role })
        header_template = loader.get_template('curation/rule_dataset_header.html').render(context)
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

            return redirect('role', role_id=role.pk)
        else:
            template = loader.get_template('curation/add_rule.html')
            header_template = loader.get_template('curation/rule_dataset_header.html').render(context)

            context.update({
                'form': form,
                'header': header_template,
            })

        return redirect('role', role_id=role.pk)

    return HttpResponse(template.render(context))

@staff_member_required
@check_rules('can_update_user_module')
def add_crud_rule(request, role_id, user_id=None):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = RequestContext(request, {
        'curation_section': 'users',
        'role': role,
    })

    if request.method == 'GET':
        template = loader.get_template('curation/add_rule.html')
        header_template = loader.get_template('curation/rule_crud_header.html').render(context)

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

            return redirect('role', role_id=role.pk)
        else:
            template = loader.get_template('curation/add_rule.html')
            header_template = loader.get_template('curation/rule_crud_header.html').render(context)

            context.update({
                'form': form,
                'header_template': header_template,
            })

        return redirect('role', role_id=role.pk)

    return HttpResponse(template.render(context))

@staff_member_required
@check_rules('can_update_user_module')
def add_field_rule(request, role_id, user_id=None, object_type=AccessRule.CITATION):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = RequestContext(request, {
        'curation_section': 'users',
        'role': role,
    })

    if request.method == 'GET':
        template = loader.get_template('curation/add_rule.html')
        if object_type == AccessRule.CITATION:
            form = FieldRuleCitationForm(initial = { 'role': role, 'object_type': object_type})
            header_template = 'curation/rule_field_citation_header.html'
        else:
            form = FieldRuleAuthorityForm(initial = { 'role': role, 'object_type': object_type})
            header_template = 'curation/rule_field_authority_header.html'

        header_template = loader.get_template(header_template).render(context)
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

            return redirect('role', role_id=role.pk)
        else:
            template = loader.get_template('curation/add_rule.html')
            header_template = loader.get_template(header_template).render(context)

            context.update({
                'form': form,
                'header': header_template,
            })

        return redirect('role', role_id=role.pk)

    return HttpResponse(template.render(context))

@staff_member_required
@check_rules('can_update_user_module')
def add_user_module_rule(request, role_id):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = RequestContext(request, {
        'curation_section': 'users',
        'role': role,
    })

    if request.method == 'GET':
        template = loader.get_template('curation/add_rule.html')
        form = UserModuleRuleForm()

        header_template = loader.get_template('curation/rule_user_module_header.html').render(context)
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

            return redirect('role', role_id=role.pk)
        else:
            template = loader.get_template('curation/add_rule.html')
            header_template = loader.get_template('curation/rule_user_module_header.html').render(context)

            context.update({
                'form': form,
                'header_template': header_template,
            })

        return redirect('role', role_id=role.pk)

    return HttpResponse(template.render(context))

@staff_member_required
@check_rules('can_update_user_module')
def add_role_to_user(request, user_edit_id, user_id=None):
    user = get_object_or_404(User, pk=user_edit_id)

    context = RequestContext(request, {
        'curation_section': 'users',
    })

    if request.method == 'GET':
        template = loader.get_template('curation/add_role_to_user.html')
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
                return redirect('user', user.pk)

            return redirect('user_list')

    return HttpResponse(template.render(context))

@staff_member_required
@check_rules('can_update_user_module')
def remove_rule(request, role_id, rule_id):
    role = get_object_or_404(IsisCBRole, pk=role_id)
    rule = get_object_or_404(AccessRule, pk=rule_id)

    if request.method == 'POST':
        rule.delete()

    return redirect('role', role_id=role.pk)


@staff_member_required
def quick_and_dirty_citation_search(request):
    q = request.GET.get('q', None)
    if not q or len(q) < 3:
        return JsonResponse({'results': []})

    queryset = Citation.objects.all()
    for part in q.split():
        queryset = queryset.filter(title__icontains=part)
    results = [{
        'id': obj.id,
        'type': obj.get_type_controlled_display(),
        'title': _get_citation_title(obj),
        'authors': _get_authors_editors(obj),
        'datestring': _get_datestring_for_citation(obj),
        'description': obj.description,
        'url': reverse("curate_citation", args=(obj.id,)),
        'public':obj.public,
    } for obj in queryset[:20]]
    return JsonResponse({'results': results})


@staff_member_required
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

    return redirect('user', user_id=user_id)

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

    return redirect('user', user_id=user_id)


@check_rules('can_update_user_module')
def add_zotero_rule(request, role_id):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = RequestContext(request, {
        'curation_section': 'users',
        'role': role,
    })

    if request.method == 'POST':
        rule = ZoteroRule.objects.create(role_id=role_id)

    return redirect('role', role_id=role.pk)
