from __future__ import absolute_import
from __future__ import unicode_literals

from builtins import str
from django.shortcuts import get_object_or_404
from isisdata.models import *

import rules


@rules.predicate
def is_accessible_by_dataset(user, obj):
    """
    Checks if the user has a role that has a dataset rule that applies to
    ``obj``.
    """
    # if user is superuser they can always do everything
    if user.is_superuser:
        return True
    
    roles = user.isiscb_roles.all()

    # if user is tenant admin, they have access to all datasets
    # we don't need to check if the tenant is the right one, as a user can only have
    # access to one tenant, and that will be checked by the tenant rule
    tenant_roles = roles.filter(accessrule__tenantrule__tenant__isnull=False)
    if tenant_roles:
        if tenant_roles.first().tenant_rules[0].allowed_action == TenantRule.UPDATE:
            return True


    dataset = getattr(obj, 'belongs_to', None)
    
    if dataset:
        roles = roles.filter(Q(accessrule__datasetrule__dataset=dataset.id)\
                            | Q(accessrule__tenantrule__tenant__default_dataset__id=dataset.id))
    else:
        roles = roles.filter((Q(accessrule__datasetrule__dataset__isnull=True)\
                              | Q(accessrule__datasetrule__dataset=''))\
                             & Q(accessrule__datasetrule__isnull=False))
    return roles.count() > 0

@rules.predicate
def is_generic_obj_accessible_by_tenant(user, obj):
    have_source_attribute = ['Attribute']
    have_subject_attribute = ['LinkedData', 'CCRelation']
    have_object_attribute = ['CCRelation']
    have_authority_attribute = []
    have_citation_attribute = ['ACRelation']

    if type(obj).__name__ in have_source_attribute:
        return is_accessible_by_tenant(user, getattr(obj, 'source', None))
    if type(obj).__name__ in have_subject_attribute:
        return is_accessible_by_tenant(user, getattr(obj, 'subject', None))
    if type(obj).__name__ in have_object_attribute:
        return is_accessible_by_tenant(user, getattr(obj, 'object', None))
    if type(obj).__name__ in have_authority_attribute:
        return is_accessible_by_tenant(user, getattr(obj, 'authority', None))
    if type(obj).__name__ in have_citation_attribute:
        return is_accessible_by_tenant(user, getattr(obj, 'citation', None))
    
    return is_accessible_by_tenant(user, obj)



@rules.predicate
def is_accessible_by_tenant(user, obj):
    """
    Checks if the user has a role that has a tenant rule that applies to
    ``obj``.
    """
    # if user is superuser they can always do everything
    if user.is_superuser:
        return True

    roles = user.isiscb_roles.all()
    tenants = getattr(obj, 'tenants', None)
    owner = getattr(obj, 'owning_tenant', None)
    all_tenants = list(tenants.all())
    if owner:
        all_tenants.append(owner)
    if tenants:
        roles = roles.filter(accessrule__tenantrule__tenant__in=[t.id for t in all_tenants])
    else:
        roles = roles.filter((Q(accessrule__tenantrule__tenant__isnull=True)\
                              | Q(accessrule__tenantrule__tenant=''))\
                             & Q(accessrule__tenantrule__isnull=False))
    return roles.count() > 0


@rules.predicate
def can_view_citation_field(user, object):
    return is_field_action_allowed(user, object, FieldRule.CANNOT_VIEW, AccessRule.CITATION)



@rules.predicate
def can_update_citation_field(user, object):
    return is_field_action_allowed(user, object, FieldRule.CANNOT_UPDATE, AccessRule.CITATION)



@rules.predicate
def can_view_authority_field(user, object):
    return is_field_action_allowed(user, object, FieldRule.CANNOT_VIEW, AccessRule.AUTHORITY)


@rules.predicate
def can_update_authority_field(user, object):
    return is_field_action_allowed(user, object, FieldRule.CANNOT_UPDATE, AccessRule.AUTHORITY)


def is_field_action_allowed(user, object, action, object_type):
    # if user is superuser they can always do everything
    if user.is_superuser:
        return True

    field_name = object[0]

    # get the object we're testing on to get the dataset
    access_obj = None
    if object_type == AccessRule.CITATION:
        access_obj = Citation.objects.get(pk=object[1])
    else:
        access_obj = Authority.objects.get(pk=object[1])


    roles = IsisCBRole.objects.filter(users__pk=user.pk)
    is_allowed = True
    for role in roles:
        # let's see if this rule has a limited record set
        has_ds_rule = has_dataset_rule(role)

        if not has_ds_rule:
            for rule in role.field_rules:
                if rule.field_name == field_name and rule.field_action == action and rule.object_type == object_type:
                    is_allowed =  False

        # if there is a dataset rule, and the object belongs to this dataset
        # we need to apply dataset rule actions
        datasets = [rule.dataset for rule in role.dataset_rules]

        # if there is a dataset rule for the given dataset
        ds_of_object = str(access_obj.belongs_to.pk) if access_obj.belongs_to else ''
        if has_ds_rule and ds_of_object in datasets:
            for rule in role.field_rules:
                # if there is a rule restricting access return False
                # dataset rules are applied before everything
                if rule.field_name == field_name and rule.field_action == action and rule.object_type == object_type:
                    return False
            # if there is a dataset rule, and access to field is not restricted provide access
            return True

    # if there are no field rules defined that disallow acces, grant access
    return is_allowed


@rules.predicate
def can_view_record(user, object):
    return is_action_allowed(user, object, CRUDRule.VIEW)


@rules.predicate
def can_view_citation_record_using_id(user, object):
    access_obj = Citation.objects.get(pk=object[1])
    return is_action_allowed(user, access_obj, CRUDRule.VIEW)


@rules.predicate
def can_view_authority_record_using_id(user, object):
    access_obj = Authority.objects.get(pk=object[1])
    return is_action_allowed(user, access_obj, CRUDRule.VIEW)


@rules.predicate
def can_edit_record(user, object):
    return is_action_allowed(user, object, CRUDRule.UPDATE)


@rules.predicate
def can_edit_citation_record_using_id(user, object):
    access_obj = Citation.objects.get(pk=object[1])
    return is_action_allowed(user, access_obj, CRUDRule.UPDATE)


@rules.predicate
def can_edit_authority_record_using_id(user, object):
    access_obj = Authority.objects.get(pk=object[1])
    return is_action_allowed(user, access_obj, CRUDRule.UPDATE)


@rules.predicate
def can_create_record(user, object):
    return is_action_allowed(user, object, CRUDRule.CREATE)


@rules.predicate
def can_create_citation_record_using_id(user, object):
    access_obj = Citation.objects.get(pk=object[1])
    return is_action_allowed(user, access_obj, CRUDRule.CREATE)


@rules.predicate
def can_create_authority_record_using_id(user, object):
    access_obj = Authority.objects.get(pk=object[1])
    return is_action_allowed(user, access_obj, CRUDRule.CREATE)


@rules.predicate
def can_delete_record(user, object):
    return is_action_allowed(user, object, CRUDRule.DELETE)


@rules.predicate
def can_delete_citation_record_using_id(user, object):
    access_obj = Citation.objects.get(pk=object[1])
    return is_action_allowed(user, access_obj, CRUDRule.DELETE)


@rules.predicate
def can_delete_authority_record_using_id(user, object):
    access_obj = Authority.objects.get(pk=object[1])
    return is_action_allowed(user, access_obj, CRUDRule.DELETE)


def is_action_allowed(user, obj, action):
    # if user is superuser they can always do everything
    if user.is_superuser:
        return True
    roles = user.isiscb_roles.all()
    dataset = getattr(obj, 'belongs_to', None)

    relevant_roles = roles
    query = (Q(accessrule__datasetrule__dataset__isnull=True) \
         | Q(accessrule__datasetrule__dataset='')) \
         & Q(accessrule__datasetrule__isnull=False)
    if dataset:
        query = Q(accessrule__datasetrule__dataset=dataset.id) \
                | Q(accessrule__tenantrule__tenant__default_dataset__id=dataset.id)

    tenants = getattr(obj, 'tenants', None)
    owner = getattr(obj, 'owning_tenant', None)
    all_tenants = list(tenants.all())
    if owner:
        all_tenants.append(owner)
    
    if all_tenants:
        query = query | Q(accessrule__tenantrule__tenant__in=[t.id for t in all_tenants])

    relevant_roles = roles.filter(query)

    grant_roles = roles.filter(pk__in=relevant_roles.values_list('id', flat=True))
    if grant_roles.count() > 0:
        return grant_roles.filter(accessrule__crudrule__crud_action=action).count() > 0
    return False


def has_dataset_rule(role):
    has_ds_rule = False
    if len(role.dataset_rules) > 0:
        has_ds_rule = True
    return has_ds_rule


@rules.predicate
def can_view_user_module(user):
    return is_user_module_action_allowed(user, UserModuleRule.VIEW)


@rules.predicate
def can_update_user_module(user):
    return is_user_module_action_allowed(user, UserModuleRule.UPDATE)


def is_user_module_action_allowed(user, action):
    # if user is superuser they can always do everything
    if user.is_superuser:
        return True

    roles = IsisCBRole.objects.filter(users__pk=user.pk)
    for role in roles:
        rules = role.user_module_rules
        for rule in rules:
            if rule.module_action == action:
                return True
    return False


@rules.predicate
def is_user_staff(user, object):
    return user.is_staff


@rules.predicate
def is_user_superuser(user, object):
    return user.is_superuser


@rules.predicate
def has_zotero_access(user):
    # if user is superuser they can always do everything
    if user.is_superuser:
        return True

    roles = IsisCBRole.objects.filter(users__pk=user.pk)
    for role in roles:
        if role.zotero_rules:
            return True

    return False

rules.add_rule('is_accessible_by_dataset',is_accessible_by_dataset)
rules.add_rule('can_view_record', can_view_record)
rules.add_rule('can_edit_record', can_edit_record)
rules.add_rule('can_create_record', can_create_record)
rules.add_rule('can_delete_record', can_delete_record)

rules.add_rule('can_view_citation_field', can_view_citation_field & can_view_citation_record_using_id)
rules.add_rule('can_update_citation_field', can_update_citation_field & can_edit_citation_record_using_id)

rules.add_rule('can_view_authority_field', can_view_authority_field & can_view_authority_record_using_id)
rules.add_rule('can_update_authority_field', can_update_authority_field & can_edit_authority_record_using_id)

rules.add_rule('is_user_staff', is_user_staff)
rules.add_rule('is_user_superuser', is_user_superuser)
rules.add_rule('can_view_user_module', can_view_user_module)
rules.add_rule('can_update_user_module', can_update_user_module)

can_access_and_view = is_accessible_by_dataset & can_view_record & is_accessible_by_tenant
rules.add_rule('can_access_and_view', can_access_and_view)

can_access_view_edit = is_accessible_by_dataset & can_view_record & can_edit_record & is_accessible_by_tenant
rules.add_rule('can_access_view_edit', can_access_view_edit)

rules.add_rule('has_zotero_access', has_zotero_access)
rules.add_rule('is_accessible_by_tenant', is_accessible_by_tenant)
rules.add_rule('is_generic_obj_accessible_by_tenant', is_generic_obj_accessible_by_tenant)