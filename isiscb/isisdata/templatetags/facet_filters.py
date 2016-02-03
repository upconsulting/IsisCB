from django import template
from isisdata.models import *
from isisdata.templatetags.app_filters import *

register = template.Library()

@register.filter
def get_author_name(author_id):
    try:
        author = Authority.objects.get(id=author_id)
        name = author.name
    except:
        name = author_id
    return name
