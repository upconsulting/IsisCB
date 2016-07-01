from django import template
from isisdata.models import *

register = template.Library()

@register.filter
def roles(userid):
    return IsisCBRole.objects.filter(users__pk=userid)

@register.filter
def print_roles(roles):
    return ", ".join(map((lambda role: role.name), roles))

@register.filter
def needs_view_rule(crud_rules):
    can_read = False
    for rule in crud_rules:
        if rule.crud_action == CRUDRule.VIEW:
            can_read = True

    if len(crud_rules) > 0 and not can_read:
        return True

    return False

@register.filter
def create_perm_tuple(fieldname, id):
    return (fieldname, id)

@register.filter
def is_public_inconsistent(instance):
    if instance.public and instance.record_status_value != 'Active':
        return True
    if not instance.public and instance.record_status_value == 'Active':
        return True
    return False

@register.filter
def are_related_objects_for_citation_public(citation):
    for acrel in citation.acrelations:
        if not acrel.public:
            return False
        if not acrel.authority.public:
            return False

    for ccrel in citation.ccrelations:
        if not ccrel.public:
            return False
        if not ccrel.object.public:
            return False

    for attr in citation.attributes.all():
        if not attr.public:
            return False

    return True

@register.filter
def are_related_objects_for_authority_public(authority):
    for acrel in authority.acrelations:
        if not acrel.public:
            return False
        if not acrel.citation.public:
            return False

    for aarel in authority.aarelations:
        if not aarel.public:
            return False
        if not aarel.object.public:
            return False

    for attr in authority.attributes.all():
        if not attr.public:
            return False

    return True

@register.filter
def get_dataset_name(ds_id):
    return Dataset.objects.get(pk=ds_id).name
