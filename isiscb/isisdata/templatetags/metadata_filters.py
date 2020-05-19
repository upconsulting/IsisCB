from __future__ import absolute_import
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import str
from django import template
from isisdata.models import *

from .app_filters import *

import urllib.request, urllib.parse, urllib.error
from collections import OrderedDict


register = template.Library()


@register.filter
def get_coins_dict(citation):
    metadata_dict = {}

    for linked_data in citation.linkeddata_entries.all():
        if linked_data.type_controlled.name == 'DOI':
            metadata_dict['rft_id'] = ['info:doi/' + linked_data.universal_resource_name]
        if linked_data.type_controlled.name == 'ISBN':
            metadata_dict['rft.isbn'] = [linked_data.universal_resource_name]

    metadata_dict['rft_val_fmt'] = ['info:ofi/fmt:kev:mtx:journal']
    if citation.type_controlled == 'BO':
        metadata_dict['rft_val_fmt'] = ['info:ofi/fmt:kev:mtx:book']
    if citation.type_controlled == 'TH':
        metadata_dict['rft_val_fmt'] = ['info:ofi/fmt:kev:mtx:dissertation']
    #metadata_dict['rft.genre'] = 'article'
    metadata_dict['rft.title'] = [bleach_safe(get_title(citation))]

    authors = citation.acrelation_set.filter(type_controlled__in=['AU'])
    metadata_dict['rft.au'] = []
    for author in authors:
        if (author.authority):
            metadata_dict['rft.au'].append(author.authority.name)

    metadata_dict['rft.date'] = [get_pub_year(citation)]
    return metadata_dict


@register.filter
def get_metatag_fields(citation):
    metadata_dict = {}

    for linked_data in citation.linkeddata_entries.all():
        if linked_data.type_controlled.name == 'DOI':
            metadata_dict['citation_doi'] = [linked_data.universal_resource_name]
        if linked_data.type_controlled.name == 'ISBN':
            metadata_dict['citation_isbn'] = [linked_data.universal_resource_name]

    metadata_dict['citation_title'] = [bleach_safe(get_title(citation))]

    authors = citation.acrelation_set.filter(type_controlled__in=['AU'])
    metadata_dict['citation_author'] = []
    for author in authors:
        if author.authority:
            metadata_dict['citation_author'].append(author.authority.name)
    metadata_dict['citation_publication_date'] = [get_pub_year(citation)]
    metadata_dict['citation_abstract'] = [bleach_safe(citation.abstract)]

    publisher = citation.acrelation_set.filter(type_controlled__in=['PU'])
    metadata_dict['citation_publisher'] = []
    for pub in publisher:
        if pub.authority:
            metadata_dict['citation_publisher'].append(pub.authority.name)
    metadata_dict['dc.type'] = [citation.get_type_controlled_display]

    periodicals = citation.acrelation_set.filter(type_controlled__in=['PE'])
    metadata_dict['citation_journal_title'] = []
    if periodicals:
        for peri in periodicals:
            if peri.authority:
                metadata_dict['citation_journal_title'].append(peri.authority.name)

    schools = citation.acrelation_set.filter(type_controlled__in=['SC'])
    metadata_dict['citation_dissertation_institution'] = []
    if schools:
        for school in schools:
            if school.authority:
                metadata_dict['citation_dissertation_institution'] = [school.authority.name]

    if citation.part_details.volume:
        metadata_dict['citation_volume'] = [citation.part_details.volume]
    elif citation.part_details.volume_free_text:
        metadata_dict['citation_volume'] = [citation.part_details.volume_free_text]

    if citation.part_details.issue_begin:
        metadata_dict['citation_issue'] = [str(citation.part_details.issue_begin)]
    if citation.part_details.issue_end:
        metadata_dict['citation_issue'] += " - " + [str(citation.part_details.issue_end)]

    if citation.part_details.page_begin:
        metadata_dict['citation_firstpage'] = [str(citation.part_details.page_begin)]
    if citation.part_details.page_end:
        metadata_dict['citation_lastpage'] = [str(citation.part_details.page_end)]

    metadata_dict['citation_language'] = []
    if citation.language.all():
        for lang in citation.language.all():
            metadata_dict['citation_language'] = [lang.id]

    return metadata_dict


@register.filter
def get_coins_from_result(result):
    """
    Generate a COinS metadata string from a search result, for embedding in
    HTML.

    TODO: support additional COinS metadata types (beyond article and book).
    """

    # If the search index is out of sync with the database, this function may
    #  be called with a result does that exist. Unless we die quietly here we
    #  risk bringing down the whole template rendering process in the search
    #  result view.
    if result is None:
        return u''

    kv_pairs = OrderedDict()
    kv_pairs['ctx_ver'] = 'Z39.88-2004'
    kv_pairs['rft_val_fmt'] = 'info:ofi/fmt:kev:mtx:book'

    # DOI & ISBN
    if result.doi:
        kv_pairs['rft_id'] = 'info:doi/%s' % result.doi
    if result.isbn:
        kv_pairs['rft.isbn'] = result.isbn

    # Publication date.
    if result.publication_date:
        kv_pairs['rft.date'] = result.publication_date[0] # Year only.

    # First author full name.
    if result.authors:
        kv_pairs['rft.au'] = result.authors[0].encode('utf-8')

    if result.type in ['Article', 'Review']:    # Article or review.
        kv_pairs['rft_val_fmt'] = 'info:ofi/fmt:kev:mtx:journal'

        # Title of the article.
        kv_pairs['rft.atitle'] = result.title.encode('utf-8')

        # Journal title.
        if len(result.periodicals) > 0:
            kv_pairs['rft.jtitle'] = result.periodicals[0].encode('utf-8')

        # Start and end pages.
        if result.page_string:
            kv_pairs['rft.pages'] = result.page_string

        for field in ['volume', 'issue', 'pages']:
            if getattr(result, field) is not None:
                kv_pairs['rft.' + field] = getattr(result, field)
    else:
        # Title of the work (e.g. book).
        kv_pairs['rft.title'] = result.title.encode('utf-8')

    return urllib.parse.urlencode(kv_pairs)


@register.filter
def get_coins_from_citation(citation):
    """
    Generate a COinS metadata string from a search result, for embedding in
    HTML.
    """
    kv_pairs = OrderedDict()
    kv_pairs['ctx_ver'] = 'Z39.88-2004'
    if citation.type_controlled in ['RE', 'AR']:
        kv_pairs['rft_val_fmt'] = 'info:ofi/fmt:kev:mtx:journal'
    if citation.type_controlled == 'BO':
        kv_pairs['rft_val_fmt'] = 'info:ofi/fmt:kev:mtx:book'
    if citation.type_controlled == 'TH':
        kv_pairs['rft_val_fmt'] = 'info:ofi/fmt:kev:mtx:dissertation'

    for linked_data in citation.linkeddata_entries.all():
        if linked_data.type_controlled.name == 'DOI':
            kv_pairs['rft_id'] = 'info:doi/' + linked_data.universal_resource_name
        if linked_data.type_controlled.name == 'ISBN':
            kv_pairs['rft.isbn'] = linked_data.universal_resource_name

    # For journal articles, we use `jtitle` for the name of the publication,
    # and `atitle` for the title of the article.
    if citation.type_controlled in ['RE', 'AR']:
        journal = citation.acrelations.filter(type_controlled='PE')
        if journal.count() > 0:
            if journal[0].authority:
                kv_pairs['rft.jtitle'] = journal[0].authority.name.encode('utf-8')
        kv_pairs['rft.atitle'] = citation.title.encode('utf-8')

    else:   # Otherwise, we use title for the work itself.
        kv_pairs['rft.title'] = bleach_safe(get_title(citation)).encode('utf-8')

    authors = citation.acrelation_set.filter(type_controlled__in=['AU'])
    if authors.count() > 0:
        if authors[0].authority:
            kv_pairs['rft.au'] = authors[0].authority.name.encode('utf-8')
    kv_pairs['rft.date'] = get_pub_year(citation)

    if citation.part_details:
        if citation.part_details.volume:
            kv_pairs['rft.volume'] = citation.part_details.volume
        if citation.part_details.issue_begin:
            kv_pairs['rft.issue'] = citation.part_details.issue_begin
        if citation.part_details.page_begin:
            kv_pairs['rft.spage'] = citation.part_details.page_begin
        if citation.part_details.page_end:
            kv_pairs['rft.epage'] = citation.part_details.page_end

    return urllib.parse.urlencode(kv_pairs)
