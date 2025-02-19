from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

from django.contrib.admin.views.decorators import staff_member_required, user_passes_test
from django.shortcuts import get_object_or_404, render, redirect
from django.template.loader import get_template
from django.contrib import messages

from django.core.paginator import Paginator, EmptyPage

from isisdata.models import *
from curation.forms import *

from curation.contrib.views import check_rules
import curation.curation_util as cutils

PAGE_SIZE = 40    # TODO: this should be configurable.


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
@check_rules('can_update_user_module')
def add_role(request, user_id=None):
    context = {
        'curation_section': 'users',
    }
    
    if request.method == 'GET':
        template = 'curation/add_role.html'
        form = RoleForm(user=request.user)
        context.update({
            'form': form,
        })
    elif request.method == 'POST':
        form = RoleForm(request.user, request.POST)

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
    
    if not request.user.is_superuser and role.tenant and role.tenant != cutil.get_tenant(request.user):
        template = 'curation/access_denied.html'

    context = {
        'curation_section': 'users',
        'role': role,
    }

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_view_user_module')
def roles(request):
    if request.user.is_superuser:
        roles = IsisCBRole.objects.all()
    else:
        tenant_rules = TenantRule.objects.filter(tenant=cutil.get_tenant(request.user))
        roles = set([rule.role for rule in tenant_rules])

    template = 'curation/roles.html'
    context = {
        'curation_section': 'users',
        'roles': roles,
    }

    return render(request, template, context)

@user_passes_test(lambda u: u.is_superuser)
@check_rules('can_update_user_module')
def add_tenant_rule(request, role_id, user_id=None):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = {
        'curation_section': 'users',
        'role': role,
    }

    if request.method == 'GET':
        template = 'curation/add_rule.html'
        form = TenantRuleForm(initial = { 'role': role })
        header_template = get_template('curation/rule_dataset_header.html').render(context)
        context.update({
            'form': form,
            'header': header_template
        })
    elif request.method == 'POST':
        if role.tenant_rules:
            return redirect('curation:role', role_id=role.pk)

        form = TenantRuleForm(request.POST)
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

def modify_tenant_rule(request, role_id, rule_id):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = {
        'curation_section': 'users',
        'role': role,
    }

    tenant_access = cutil.get_tenant_access(request.user, cutil.get_tenant(request.user))

    # Is user allowed to change tenant?
    if request.method == 'POST' and tenant_access == TenantRule.UPDATE:
        rule = get_object_or_404(TenantRule, pk=rule_id)
        permission = request.POST.get('allowed_action', TenantRule.VIEW)
        # we dont' just want to pass a random string through
        if permission == TenantRule.UPDATE:
            rule.allowed_action = TenantRule.UPDATE
        else:
            rule.allowed_action = TenantRule.VIEW
        rule.save()

    return redirect('curation:role', role_id=role.pk)


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
        form = DatasetRuleForm(request.user, initial = { 'role': role })
        header_template = get_template('curation/rule_dataset_header.html').render(context)
        context.update({
            'form': form,
            'header': header_template
        })
    elif request.method == 'POST':
        form = DatasetRuleForm(request.user, request.POST)

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
        form = AddRoleForm(user=request.user, initial = { 'users': user })
        context.update({
            'form': form,
        })
    elif request.method == 'POST':
        form = AddRoleForm(request.user, request.POST)

        if form.is_valid():
            role_id = form.cleaned_data['role']
            role = get_object_or_404(IsisCBRole, pk=role_id)
            if role.tenant_rules:
                tenants = set([rule.tenant for rule in role.tenant_rules])
                tenants_of_user = list(cutils.get_tenants(user))
                tenant_to_add = None
                
                # if for some reason two tenant rules are being added for different tenants
                if len(tenants) > 1:
                    messages.add_message(request, messages.ERROR, "Users can only belong two one tenant.")
                else:
                    tenant_to_add = tenants.pop()

                if tenant_to_add:
                    # if user already belongs to another tenant
                    if tenants_of_user and tenant_to_add not in tenants_of_user:
                        messages.add_message(request, messages.ERROR, "User already belongs to a tenant. You cannot add a second tenant role.")
                    else:
                        role.users.add(user)
                        role.save()
                else:
                    messages.add_message(request, messages.ERROR, "Tenant rule was submitted with a tenant.")
            else:
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
