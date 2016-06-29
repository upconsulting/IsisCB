from __future__ import absolute_import

from django.template import RequestContext, loader
from django.contrib.admin.views.decorators import staff_member_required, user_passes_test

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse #, HttpResponseForbidden, Http404, , JsonResponse
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.shortcuts import redirect

from rules.contrib.views import permission_required, objectgetter
from .rules import is_accessible_by_dataset
from django.forms import modelform_factory

from isisdata.models import *
from curation.filters import *
from curation.forms import *
from curation.contrib.views import check_rules

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
#@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
@staff_member_required
def acrelation_for_citation(request, citation_id, acrelation_id=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    acrelation = None
    if acrelation_id:
        acrelation = get_object_or_404(ACRelation, pk=acrelation_id)

    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'acrelation': acrelation,
    })
    if request.method == 'GET':
        if acrelation:
            form = ACRelationForm(instance=acrelation, prefix='acrelation')
        else:
            form = ACRelationForm(prefix='acrelation', initial={'citation': citation.id})

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
        return HttpResponseRedirect(reverse('curate_authority', args=(authority.id,)) + '?tab=attributes')
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
        context.update({'tab': request.GET.get('tab', None)})
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

@staff_member_required
def user(request, user_id):
    selected_user = get_object_or_404(User, pk=user_id)


    context = RequestContext(request, {
        'curation_section': 'users',
        'selected_user': selected_user,
    })
    template = loader.get_template('curation/user.html')
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
def remove_role(request, user_id, role_id):
    role = get_object_or_404(IsisCBRole, pk=role_id)
    user = get_object_or_404(User, pk=user_id)

    role.users.remove(user)

    return redirect('user', user_id=user.pk)

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
        else:
            form = FieldRuleAuthorityForm(initial = { 'role': role, 'object_type': object_type})

        header_template = loader.get_template('curation/rule_field_citation_header.html').render(context)
        context.update({
            'form': form,
            'header': header_template
        })
    elif request.method == 'POST':
        if object_type == AccessRule.CITATION:
            form = FieldRuleCitationForm(request.POST)
        else:
            form = FieldRuleAuthorityForm(request.POST)


        if form.is_valid():
            rule = form.save()
            rule.object_type = object_type
            rule.role = role
            rule.save()

            return redirect('role', role_id=role.pk)
        else:
            template = loader.get_template('curation/add_rule.html')
            header_template = loader.get_template('curation/rule_field_citation_header.html').render(context)

            context.update({
                'form': form,
                'header': header_template,
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

            if request.GET.get('from_user', False):
                return redirect('user', user.pk)

            return redirect('user_list')

    return HttpResponse(template.render(context))

@staff_member_required
def remove_rule(request, role_id, rule_id):
    role = get_object_or_404(IsisCBRole, pk=role_id)
    rule = get_object_or_404(AccessRule, pk=rule_id)

    rule.delete()

    return redirect('role', role_id=role.pk)

@staff_member_required
def quick_and_dirty_authority_search(request):
    q = request.GET.get('q', None)
    if not q or len(q) < 3:
        return JsonResponse({'results': []})

    queryset = Authority.objects.all()
    for part in q.split():
        queryset = queryset.filter(name__icontains=part)
    results = [{
        'id': obj.id,
        'type': obj.get_type_controlled_display(),
        'name': obj.name,
        'description': obj.description,
        'url': obj.get_absolute_url(),
    } for obj in queryset[:20]]
    return JsonResponse({'results': results})
