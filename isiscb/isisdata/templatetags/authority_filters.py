from django import template
from isisdata.models import *

register = template.Library()

@register.filter
def is_person(authority):
    return authority.type_controlled == Authority.PERSON
