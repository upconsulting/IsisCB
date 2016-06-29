from __future__ import absolute_import

from django.shortcuts import get_object_or_404
from isisdata.models import *

from rules import predicate

@predicate
def is_accessible_by_dataset(user, object):
    """
    Checks if the user has a role that has a dataset rule that allows
    the user to see the current object.
    """
    # if user is superuser they can always do everything
    if user.is_superuser:
        return True

    roles = IsisCBRole.objects.filter(users__pk=user.pk)
    has_dataset_rules = False
    for role in roles:
        rules = role.dataset_rules
        if rules:
            has_dataset_rules = True
        for rule in rules:
            if rule.dataset == object.dataset:
                return True
    # if there are no dataset rules on any role then the user
    # has access to all records
    if not has_dataset_rules:
        return True
    return False

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
        if has_ds_rule and access_obj.dataset in datasets:
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

def is_action_allowed(user, object, action):
    # if user is superuser they can always do everything
    if user.is_superuser:
        return True

    roles = IsisCBRole.objects.filter(users__pk=user.pk)
    is_allowed = False
    for role in roles:
        rules = role.crud_rules

        # let's see if this rule has a limited record set
        has_ds_rule = has_dataset_rule(role)

        # if there is no limited record set, just look at the actions
        if not has_ds_rule:
            for rule in rules:
                if rule.crud_action == action:
                    is_allowed = True
        # if there is a dataset rule, and the object belongs to this dataset
        # we need to apply dataset rule actions
        datasets = [rule.dataset for rule in role.dataset_rules]

        # if this role applies, check allowed actions
        # dataset roles are applied over everthing else
        if has_ds_rule and object.dataset in datasets:
            for rule in rules:
                if rule.crud_action == action:
                    return True
            # if there is no rule to give access
            return False

    return is_allowed

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
