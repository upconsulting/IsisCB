from django import template
from isisdata.models import *

register = template.Library()

@register.filter
def get_nr_of_citations(authority):
    return ACRelation.objects.filter(authority=authority, citation__public=True).distinct('citation_id').count()
