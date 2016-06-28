from __future__ import absolute_import

from django.template import RequestContext, loader
from django.contrib.admin.views.decorators import staff_member_required, user_passes_test

from django.http import HttpResponse, HttpResponseRedirect #, HttpResponseForbidden, Http404, , JsonResponse
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.shortcuts import redirect

from rules.contrib.views import permission_required, objectgetter
from .rules import is_accessible_by_dataset

from isisdata.models import *
from curation.filters import *
from curation.forms import *

import iso8601
import rules

@staff_member_required
def dashboard(request):
    """
    """
    template = loader.get_template('curation/dashboard.html')
    context = RequestContext(request, {
    })
    return HttpResponse(template.render(context))


#@staff_member_required
#@permission_required('isiscb.view_dataset', fn=objectgetter(Citation, 'citation_id'), raise_exception=True)
def citation(request, citation_id=None):
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
    })
    if citation_id:
        citation = get_object_or_404(Citation, pk=citation_id)
        print rules.rule_exists('is_accessible_by_dataset')
        # test for dataset
        if not rules.test_rule('is_accessible_by_dataset', request.user, citation):
           template = loader.get_template('curation/access_denied.html')
           return HttpResponse(template.render(context))

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

@staff_member_required
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

            return redirect('role', role_id=role.pk)
        else:
            template = loader.get_template('curation/add_role.html')
            context.update({
                'form': form,
            })
    else:
        # for now just redirect to user page in any other case
        template = loader.get_template('curation/users.html')

    return HttpResponse(template.render(context))

@staff_member_required
def role(request, role_id, user_id=None):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    template = loader.get_template('curation/role.html')
    context = RequestContext(request, {
        'curation_section': 'users',
        'role': role,
    })

    return HttpResponse(template.render(context))

@staff_member_required
def add_dataset_rule(request, role_id, user_id=None):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = RequestContext(request, {
        'curation_section': 'users',
    })

    if request.method == 'GET':
        template = loader.get_template('curation/add_dataset_rule.html')
        form = DatasetRuleForm(initial = { 'role': role })
        context.update({
            'form': form,
            'role': role,
        })
    elif request.method == 'POST':
        form = DatasetRuleForm(request.POST)

        if form.is_valid():
            rule = form.save()
            rule.role = role
            rule.save()

            return redirect('role', role_id=role.pk)
        else:
            template = loader.get_template('curation/add_dataset_rule.html')
            context.update({
                'form': form,
            })

        return redirect('role', role_id=role.pk)

    return HttpResponse(template.render(context))

@staff_member_required
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

            return redirect('user_list')

    return HttpResponse(template.render(context))
