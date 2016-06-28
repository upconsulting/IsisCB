from django.template import RequestContext, loader
from django.contrib.admin.views.decorators import staff_member_required

from django.http import HttpResponse, HttpResponseRedirect #, HttpResponseForbidden, Http404, , JsonResponse
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User


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
