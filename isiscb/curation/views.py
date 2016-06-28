from django.template import RequestContext, loader
from django.contrib.admin.views.decorators import staff_member_required

from django.http import HttpResponse, HttpResponseRedirect #, HttpResponseForbidden, Http404, , JsonResponse
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.forms import modelform_factory

from isisdata.models import *
from curation.filters import *
from curation.forms import *

import iso8601



@staff_member_required
def dashboard(request):
    """
    """
    template = loader.get_template('curation/dashboard.html')
    context = RequestContext(request, {
    })
    return HttpResponse(template.render(context))


@staff_member_required
def delete_attribute_for_citation(request, citation_id, attribute_id):
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
        return HttpResponseRedirect(reverse('curate_citation', args=(citation.id,)) + '?tab=attributes')
    template = loader.get_template('curation/citation_attribute_delete.html')
    return HttpResponse(template.render(context))


@staff_member_required
def delete_attribute_for_authority(request, authority_id, attribute_id):
    authority = get_object_or_404(Authority, pk=authority_id)
    attribute = get_object_or_404(Attribute, pk=attribute_id)
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': authority,
        'attribute': attribute,
    })
    if request.GET.get('confirm', False):
        attribute.delete()
        return HttpResponseRedirect(reverse('curate_authority', args=(citation.id,)) + '?tab=attributes')
    template = loader.get_template('curation/authority_attribute_delete.html')
    return HttpResponse(template.render(context))


@staff_member_required
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
def citation(request, citation_id=None):
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
    })
    if citation_id:
        citation = get_object_or_404(Citation, pk=citation_id)
        template = loader.get_template('curation/citation_change_view.html')
        partdetails_form = None
        context.update({'tab': request.GET.get('tab', None)})
        if request.method == 'GET':
            form = CitationForm(instance=citation)
            context.update({
                'form': form,
                'instance': citation,
            })
            if citation.type_controlled == Citation.ARTICLE and hasattr(citation, 'part_details'):
                partdetails_form = PartDetailsForm(instance=citation.part_details)
                context.update({
                    'partdetails_form': partdetails_form,
                })
        elif request.method == 'POST':
            form = CitationForm(request.POST, instance=citation)
            if citation.type_controlled == Citation.ARTICLE and hasattr(citation, 'part_details'):
                partdetails_form = PartDetailsForm(request.POST, instance=citation.part_details)
            if form.is_valid() and (partdetails_form is None or partdetails_form.is_valid()):
                form.save()
                if partdetails_form:
                    partdetails_form.save()
                return HttpResponseRedirect(reverse('citation_list'))

            context.update({
                'form': form,
                'instance': citation,
                'partdetails_form': partdetails_form,
            })
    else:
        template = loader.get_template('curation/citation_list_view.html')
        filtered_objects = CitationFilter(request.GET, queryset=Citation.objects.all())

        context.update({
            'objects': filtered_objects,
            'filters_active': len([v for k, v in request.GET.iteritems()
                                   if len(v) > 0 and k != 'page']) > 0,
        })
    return HttpResponse(template.render(context))


@staff_member_required
def authority(request, authority_id=None):
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
    })
    if authority_id:

        authority = get_object_or_404(Authority, pk=authority_id)
        template = loader.get_template('curation/authority_change_view.html')
        person_form = None
        if request.method == 'GET':
            if authority.type_controlled == Authority.PERSON and hasattr(Authority, 'person'):
                person_form = PersonForm(instance=authority.person)

            form = AuthorityForm(instance=authority)
            context.update({
                'form': form,
                'instance': authority,
                'person_form': person_form,
            })


        elif request.method == 'POST':
            if authority.type_controlled == Authority.PERSON and hasattr(Authority, 'person'):
                person_form = PersonForm(request.POST, instance=authority.person)

            form = AuthorityForm(request.POST, instance=authority)
            if form.is_valid() and (person_form is None or person_form.is_valid()):
                form.save()
                if person_form:
                    person_form.save()
                return HttpResponseRedirect(reverse('authority_list'))

            context.update({
                'form': form,
                'person_form': person_form,
                'instance': citation,
                # 'partdetails_form': partdetails_form,
            })
    else:
        template = loader.get_template('curation/authority_list_view.html')
        filtered_objects = AuthorityFilter(request.GET, queryset=Authority.objects.all())
        context.update({
            'objects': filtered_objects,
            'filters_active': len([v for k, v in request.GET.iteritems()
                                   if len(v) > 0 and k != 'page']) > 0,
        })
    return HttpResponse(template.render(context))


@staff_member_required
def dataset(request, dataset_id=None):
    return HttpResponse('')


@staff_member_required
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
