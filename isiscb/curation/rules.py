from __future__ import absolute_import
from __future__ import unicode_literals

from builtins import str
from django.shortcuts import get_object_or_404
from isisdata.models import *

from rules import predicate



@predicate
def is_accessible_by_dataset(user, obj):
    """
    Checks if the user has a role that has a dataset rule that applies to
    ``obj``.
    """
    # if user is superuser they can always do everything
    if user.is_superuser:
        return True
    roles = user.isiscbrole_set.all()
    dataset = getattr(obj, 'belongs_to', None)
    if dataset:
        roles = roles.filter(accessrule__datasetrule__dataset=dataset.id)
    else:
        roles = roles.filter((Q(accessrule__datasetrule__dataset__isnull=True)\
                              | Q(accessrule__datasetrule__dataset=''))\
                             & Q(accessrule__datasetrule__isnull=False))
    return roles.count() > 0

@predicate
def is_accessible_by_tenant(user, obj):
    """
    Checks if the user has a role that has a dataset rule that applies to
    ``obj``.
    """
    # if user is superuser they can always do everything
    if user.is_superuser:
        return True

    roles = user.isiscbrole_set.all()
    tenants = getattr(obj, 'tenants', None)
    if tenants:
        roles = roles.filter(accessrule__tenantrule__tenant__in=[t.id for t in tenants.all()])
    else:
        roles = roles.filter((Q(accessrule__tenantrule__tenant__isnull=True)\
                              | Q(accessrule__tenantrule__tenant=''))\
                             & Q(accessrule__tenantrule__isnull=False))
    return roles.count() > 0


@predicate
def can_view_citation_field(user, object):
    return is_field_action_allowed(user, object, FieldRule.CANNOT_VIEW, AccessRule.CITATION)



@predicate
def can_update_citation_field(user, object):
    return is_field_action_allowed(user, object, FieldRule.CANNOT_UPDATE, AccessRule.CITATION)



@predicate
def can_view_authority_field(user, object):
    return is_field_action_allowed(user, object, FieldRule.CANNOT_VIEW, AccessRule.AUTHORITY)


@predicate
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


@predicate
def can_view_record(user, object):
    return is_action_allowed(user, object, CRUDRule.VIEW)


@predicate
def can_view_citation_record_using_id(user, object):
    access_obj = Citation.objects.get(pk=object[1])
    return is_action_allowed(user, access_obj, CRUDRule.VIEW)


@predicate
def can_view_authority_record_using_id(user, object):
    access_obj = Authority.objects.get(pk=object[1])
    return is_action_allowed(user, access_obj, CRUDRule.VIEW)


@predicate
def can_edit_record(user, object):
    return is_action_allowed(user, object, CRUDRule.UPDATE)


@predicate
def can_edit_citation_record_using_id(user, object):
    access_obj = Citation.objects.get(pk=object[1])
    return is_action_allowed(user, access_obj, CRUDRule.UPDATE)


@predicate
def can_edit_authority_record_using_id(user, object):
    access_obj = Authority.objects.get(pk=object[1])
    return is_action_allowed(user, access_obj, CRUDRule.UPDATE)


@predicate
def can_create_record(user, object):
    return is_action_allowed(user, object, CRUDRule.CREATE)


@predicate
def can_create_citation_record_using_id(user, object):
    access_obj = Citation.objects.get(pk=object[1])
    return is_action_allowed(user, access_obj, CRUDRule.CREATE)


@predicate
def can_create_authority_record_using_id(user, object):
    access_obj = Authority.objects.get(pk=object[1])
    return is_action_allowed(user, access_obj, CRUDRule.CREATE)


@predicate
def can_delete_record(user, object):
    return is_action_allowed(user, object, CRUDRule.DELETE)


@predicate
def can_delete_citation_record_using_id(user, object):
    access_obj = Citation.objects.get(pk=object[1])
    return is_action_allowed(user, access_obj, CRUDRule.DELETE)


@predicate
def can_delete_authority_record_using_id(user, object):
    access_obj = Authority.objects.get(pk=object[1])
    return is_action_allowed(user, access_obj, CRUDRule.DELETE)


def is_action_allowed(user, obj, action):
    # if user is superuser they can always do everything
    if user.is_superuser:
        return True
    roles = user.isiscbrole_set.all()
    dataset = getattr(obj, 'belongs_to', None)

    print("is_action_allowed")
    relevant_roles = roles
    query = (Q(accessrule__datasetrule__dataset__isnull=True) \
         | Q(accessrule__datasetrule__dataset='')) \
         & Q(accessrule__datasetrule__isnull=False)
    if dataset:
        query = Q(accessrule__datasetrule__dataset=dataset.id)

    tenants = getattr(obj, 'tenants', None)
    print(tenants)
    for t in tenants.all():
        print(t.name)
    if tenants:
        query = query | Q(accessrule__tenantrule__tenant__in=[t.id for t in tenants.all()])

    relevant_roles = roles.filter(query)
    print(relevant_roles)

    grant_roles = roles.filter(pk__in=relevant_roles.values_list('id', flat=True))
    if grant_roles.count() > 0:
        return grant_roles.filter(accessrule__crudrule__crud_action=action).count() > 0
    return False


def has_dataset_rule(role):
    has_ds_rule = False
    if len(role.dataset_rules) > 0:
        has_ds_rule = True
    return has_ds_rule


@predicate
def can_view_user_module(user):
    return is_user_module_action_allowed(user, UserModuleRule.VIEW)


@predicate
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


@predicate
def is_user_staff(user, object):
    return user.is_staff


@predicate
def is_user_superuser(user, object):
    return user.is_superuser


@predicate
def has_zotero_access(user):
    # if user is superuser they can always do everything
    if user.is_superuser:
        return True

    roles = IsisCBRole.objects.filter(users__pk=user.pk)
    for role in roles:
        if role.zotero_rules:
            return True

    return False
