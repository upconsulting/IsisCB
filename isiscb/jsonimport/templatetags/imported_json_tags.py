from django import template

from jsonimport.models import ImportedACRelation

register = template.Library()

@register.filter
def get_new_authorities(citation):
    return ImportedACRelation.objects.filter(citation=citation, authority__isnull=False).count()
    
@register.filter
def get_existing_authorities(citation):
    return ImportedACRelation.objects.filter(citation=citation, existing_authority__isnull=False).count()