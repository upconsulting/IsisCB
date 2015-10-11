from django import template
from isisdata.models import *
from isisdata.templatetags.app_filters import *

register = template.Library()

@register.filter
def get_page_string(citation):
    if citation.type_controlled != Citation.CHAPTER:
        return ""
    page_start_string = citation.part_details.page_begin
    page_end_string = citation.part_details.page_end
    if page_start_string and page_end_string:
        return "pp. " + str(page_start_string) + "-" + str(page_end_string)
    if page_start_string:
        return "p. " + str(page_start_string)
    if page_end_string:
        return "p. " + str(page_end_string)
    return ""

@register.filter
def join_authors(authors):
    author_names = []
    for author in authors:
        author_names.append(author.authority.name)
    return "; ".join(author_names)
