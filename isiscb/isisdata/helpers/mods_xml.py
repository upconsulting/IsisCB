from __future__ import absolute_import
from __future__ import unicode_literals
from builtins import str
from xml.dom.minidom import *
from isisdata.templatetags.app_filters import *
from .mods_helper import *

def initial_response(citation_id):
    doc = xml.dom.minidom.Document()
    # <formats id="http://unapi.info/news/archives/9">
    formats = doc.createElement('formats')
    formats.setAttribute('id', citation_id)
    doc.appendChild(formats)
    # <format name="mods" type="application/xml" />
    format = doc.createElement('format')
    format.setAttribute('name', 'mods')
    format.setAttribute('type', 'application/xml')
    formats.appendChild(format)

    return doc.toprettyxml(indent="    ", encoding="utf-8")

def generate_mods_xml(citation):
    # create basis for xml
    doc = xml.dom.minidom.Document()

    mods = doc.createElement('mods')
    doc.appendChild(mods)
    mods.setAttribute('xmlns', 'http://www.loc.gov/mods/v3')
    mods.setAttribute('version', '3.5')
    #doc.createElementNS('http://www.w3.org/2001/XMLSchema-instance', 'xsi')
    #mods.setAttribute('xsi:schemaLocation', 'http://www.loc.gov/mods/v3 http://www.loc.gov/standards/mods/v3/mods-3-5.xsd')

    # add titles
    titleInfo = doc.createElement('titleInfo')
    mods.appendChild(titleInfo)
    title = doc.createElement('title')
    titleInfo.appendChild(title)
    title_text = doc.createTextNode(bleach_safe(get_title(citation)))
    title.appendChild(title_text)

    # add authors
    authors = citation.acrelation_set.filter(type_controlled__in=['AU']).order_by('data_display_order')
    for author in authors:
        name = doc.createElement('name')
        name.setAttribute('type', 'personal')
        mods.appendChild(name)
        name_part = doc.createElement('namePart')
        name.appendChild(name_part)
        name_part_text = doc.createTextNode(author.authority.name)
        name_part.appendChild(name_part_text)
        # role
        role = doc.createElement('role')
        name.appendChild(role)
        role_term = doc.createElement('roleTerm')
        role_term.setAttribute('type', 'text')
        role.appendChild(role_term)
        role_term_text = doc.createTextNode('creator')
        role_term.appendChild(role_term_text)

    # add editors
    editors = citation.acrelation_set.filter(type_controlled__in=['ED'])
    for edt in editors:
        name = doc.createElement('name')
        name.setAttribute('type', 'personal')
        mods.appendChild(name)
        name_part = doc.createElement('namePart')
        name.appendChild(name_part)
        name_part_text = doc.createTextNode(edt.authority.name)
        name_part.appendChild(name_part_text)
        # role
        role = doc.createElement('role')
        name.appendChild(role)
        role_term = doc.createElement('roleTerm')
        role_term.setAttribute('type', 'text')
        role.appendChild(role_term)
        role_term_text = doc.createTextNode('editor')
        role_term.appendChild(role_term_text)

    # add contributors
    contributors = citation.acrelation_set.filter(type_controlled__in=['CO','AD'])
    for contr in contributors:
        name = doc.createElement('name')
        name.setAttribute('type', 'personal')
        mods.appendChild(name)
        name_part = doc.createElement('namePart')
        name.appendChild(name_part)
        name_part_text = doc.createTextNode(contr.authority.name)
        name_part.appendChild(name_part_text)
        # role
        role = doc.createElement('role')
        name.appendChild(role)
        role_term = doc.createElement('roleTerm')
        role_term.setAttribute('type', 'text')
        role.appendChild(role_term)
        role_term_text = doc.createTextNode('contributor')
        role_term.appendChild(role_term_text)

    # publication date
    origin_info = doc.createElement('originInfo')
    origin_info.setAttribute('eventType', 'publication')
    mods.appendChild(origin_info)
    date_issued = doc.createElement('dateIssued')
    date_issued.appendChild(doc.createTextNode(get_pub_year(citation)))
    origin_info.appendChild(date_issued)

    # add abstract
    abstract = doc.createElement('abstract')
    mods.appendChild(abstract)
    abstract.appendChild(doc.createTextNode(citation.human_readable_abstract))

    # type of resource
    genre = doc.createElement('genre')
    genre.setAttribute('authority', 'local')
    cit_type = get_type(citation.type_controlled) #citation.get_type_controlled_display().lower()
    genre.appendChild(doc.createTextNode(cit_type))
    mods.appendChild(genre)

    part = doc.createElement('part')

    # volume
    volume = get_volume(citation)
    if volume:
        detail = doc.createElement('detail')
        detail.setAttribute('type', 'volume')
        part.appendChild(detail)
        number = doc.createElement('number')
        number.appendChild(doc.createTextNode(volume))
        detail.appendChild(number)

    issue = get_issue(citation)
    if issue:
        detail = doc.createElement('detail')
        detail.setAttribute('type', 'issue')
        part.appendChild(detail)
        number = doc.createElement('number')
        number.appendChild(doc.createTextNode(issue))
        detail.appendChild(number)

    publishers = get_publisher(citation)
    for pub in publishers:
        publisher = doc.createElement('publisher')
        publisher.appendChild(doc.createTextNode(pub.authority.name))
        origin_info.appendChild(publisher)

    # Periodical
    periodicals = citation.acrelation_set.filter(type_controlled__in=['PE'])
    for periodical in periodicals:
        # create <relatedItem><titleInfo><title>
        related_item = doc.createElement('relatedItem')
        related_item.setAttribute('type', 'host')
        mods.appendChild(related_item)

        rel_title_info = doc.createElement('titleInfo')
        related_item.appendChild(rel_title_info)

        rel_title = doc.createElement('title')
        rel_title.appendChild(doc.createTextNode(periodical.authority.name))
        rel_title_info.appendChild(rel_title)
        # add volume, etc. info
        related_item.appendChild(part)


    # series
    series = citation.acrelation_set.filter(type_controlled__in=['BS'])
    for serie in series:
        # create <relatedItem><titleInfo><title>
        series_related_item = doc.createElement('relatedItem')
        series_related_item.setAttribute('type', 'host')
        mods.appendChild(series_related_item)

        series_rel_title_info = doc.createElement('titleInfo')
        series_related_item.appendChild(series_rel_title_info)

        series_rel_title = doc.createElement('title')
        series_rel_title.appendChild(doc.createTextNode(serie.authority.name))
        series_rel_title_info.appendChild(series_rel_title)

        # add volume, etc. info
        series_related_item.appendChild(part)


    # included in
    included_in = CCRelation.objects.filter(object_id=citation.id, type_controlled='IC', object__public=True)
    for included in included_in:
        # create <relatedItem><titleInfo><title>
        included_in_rel_item = doc.createElement('relatedItem')
        included_in_rel_item.setAttribute('type', 'host')
        mods.appendChild(included_in_rel_item)

        included_in_rel_item_title_info = doc.createElement('titleInfo')
        included_in_rel_item.appendChild(included_in_rel_item_title_info)

        included_in_rel_item_title = doc.createElement('title')
        included_in_rel_item_title.appendChild(doc.createTextNode(bleach_safe(get_title(included.subject))))
        included_in_rel_item_title_info.appendChild(included_in_rel_item_title)


    start_page = citation.part_details.page_begin
    end_page = citation.part_details.page_end

    if not end_page:
        end_page = start_page

    if start_page or end_page:
        extent = doc.createElement('extent')
        extent.setAttribute('unit', 'page')
        part.appendChild(extent)
        if start_page:
            start = doc.createElement('start')
            start.appendChild(doc.createTextNode(str(start_page)))
            extent.appendChild(start)
        if end_page:
            end = doc.createElement('end')
            end.appendChild(doc.createTextNode(str(end_page)))
            extent.appendChild(end)

    for linked_data in citation.linkeddata_entries.all():
        if linked_data.type_controlled.name in ['DOI', 'ISBN'] :
            identifier = doc.createElement('identifier')
            if linked_data.type_controlled.name == 'DOI':
                identifier.setAttribute('type', 'doi')
            else:
                identifier.setAttribute('type', 'isbn')
            identifier.appendChild(doc.createTextNode(linked_data.universal_resource_name))
            mods.appendChild(identifier)

    return doc.toprettyxml(indent="    ", encoding="utf-8")
