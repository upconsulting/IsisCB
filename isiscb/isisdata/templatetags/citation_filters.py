from __future__ import unicode_literals
from builtins import str
from django import template
from isisdata.models import *
from isisdata.templatetags.app_filters import *

register = template.Library()


@register.filter
def get_page_string(citation):
    if citation.type_controlled not in [Citation.CHAPTER, Citation.ARTICLE, Citation.REVIEW, Citation.ESSAY_REVIEW]:
        return ""
    if not getattr(citation, 'part_details', None):
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
def get_public_page_string(citation):
    if not citation.part_details:
        return ""
    if citation.part_details.pages_free_text:
        return citation.part_details.pages_free_text
    else:
        return citation.part_details.pages

@register.filter
def join_authors(authors, postfix):
    author_names = []
    for author in authors:
        author_names.append(contributor_as_string(author) + postfix)
    return "; ".join(author_names)


@register.filter
def get_editors(citation):
    if citation:
        return citation.acrelation_set.filter(type_controlled__in=['ED'])
    return citation

@register.filter
def get_authors(citation):
    if citation:
        return citation.acrelation_set.filter(type_controlled__in=['AU'], citation__public=True, public=True).order_by('data_display_order')
    return citation


@register.filter
def join_names_with_postfix(name_list, postfix):
    names = []
    for name in name_list:
        names.append(name + postfix)
    return "; ".join(names)


@register.filter
def get_book_title(citation):
    if citation.type_controlled in ['CH']:
        parent_relation = CCRelation.objects.filter(object_id=citation.id, type_controlled='IC')
        # we assume there is just one
        if parent_relation:
            return parent_relation[0].subject.title

    return ""

@register.filter
def get_journal_title(citation):
    if citation.type_controlled in [Citation.ARTICLE, Citation.REVIEW, Citation.ESSAY_REVIEW]:
        parent_relation = ACRelation.objects.filter(citation=citation.id, type_controlled=ACRelation.PERIODICAL)
        # we assume there is just one
        if parent_relation and len(parent_relation) > 0 and parent_relation[0].authority:
            return parent_relation[0].authority.name

    return ""

@register.filter
def get_school(citation):
    if citation.type_controlled in [Citation.THESIS]:
        parent_relation = ACRelation.objects.filter(citation=citation.id, type_controlled=ACRelation.SCHOOL)
        # we assume there is just one
        if parent_relation:
            return parent_relation[0].authority.name

    return ""

@register.filter
def contributor_with_role_as_string(acrelation):
    name = acrelation.name_for_display_in_citation
    if not name:
        name = acrelation.authority.name
    kwargs = {'name': name,
              'role': acrelation.get_type_controlled_display()}
    return u"{name} ({role})".format(**kwargs)
