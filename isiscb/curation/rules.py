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
    print "here"
    print user
    roles = IsisCBRole.objects.filter(users__pk=user.pk)
    print roles
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
