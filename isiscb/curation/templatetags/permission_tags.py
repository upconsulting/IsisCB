from django import template
from isisdata.models import *

register = template.Library()

@register.filter
def roles(userid):
    return IsisCBRole.objects.filter(users__pk=userid)

@register.filter
def print_roles(roles):
    return ", ".join(map((lambda role: role.name), roles))
