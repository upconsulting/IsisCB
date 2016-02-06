from django import template
from isisdata.models import *
from isisdata.templatetags.app_filters import *

register = template.Library()

@register.filter
def get_authority_name(id):
    try:
        authority = Authority.objects.get(id=id)
        name = authority.name
    except:
        name = id
    return name
