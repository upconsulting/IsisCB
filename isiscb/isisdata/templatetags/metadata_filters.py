from django import template
from isisdata.models import *
from app_filters import *

register = template.Library()

@register.filter
def get_coins_dict(citation):
    metadata_dict = {}
    #metadata_dict['rft_val_fmt'] = 'info:ofi/fmt:kev:mtx:book'
    metadata_dict['dc.genre'] = 'book'
    metadata_dict['dc.title'] = bleach_safe(get_title(citation))
    for author in get_contributors(citation):
        metadata_dict['dc.creator'] = contributor_as_string(author)
    return metadata_dict

@register.filter
def get_metatag_fields(citation):
    metadata_dict = {}
    metadata_dict['citation_title'] = bleach_safe(get_title(citation))
    authors = citation.acrelation_set.filter(type_controlled__in=['AU'])
    for author in authors:
        metadata_dict['citation_author'] = author.authority.name
    metadata_dict['citation_publication_date'] = get_pub_year(citation)
    metadata_dict['citation_abstract'] = bleach_safe(citation.abstract)

    publisher = citation.acrelation_set.filter(type_controlled__in=['PU'])
    for pub in publisher:
        metadata_dict['citation_publisher'] = pub.authority.name
    return metadata_dict
