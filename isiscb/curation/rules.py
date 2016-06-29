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


def is_field_action_allowed(user, object, action, object_type):
    roles = IsisCBRole.objects.filter(users__pk=user.pk)
    has_rules = False
    for role in roles:
        if role.field_rules:
            has_rules = True
        for rule in role.field_rules:
            if rule.field_name == object and rule.field_action == action and rule.object_type == object_type:
                return False
    # if there are no field rules defined that disallow acces grant access
    return True

@predicate
def can_view_record(user, object):
    return is_action_allowed(user, object, CRUDRule.VIEW)

@predicate
def can_edit_record(user, object):
    return is_action_allowed(user, object, CRUDRule.UPDATE)

@predicate
def can_create_record(user, object):
    return is_action_allowed(user, object, CRUDRule.CREATE)

@predicate
def can_delete_record(user, object):
    return is_action_allowed(user, object, CRUDRule.DELETE)

def is_action_allowed(user, object, action):
    roles = IsisCBRole.objects.filter(users__pk=user.pk)
    for role in roles:
        rules = role.crud_rules
        for rule in rules:
            if rule.crud_action == action:
                return True
    return False
