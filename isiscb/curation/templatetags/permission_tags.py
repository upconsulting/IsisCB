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
