from xml.dom.minidom import *
from isisdata.templatetags.app_filters import *

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
    title_text = doc.createTextNode(citation.title)
    title.appendChild(title_text)

    # add authors
    authors = citation.acrelation_set.filter(type_controlled__in=['AU'])
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
    contributors = citation.acrelation_set.filter(type_controlled__in=['CO'])
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

    # type of resource
    genre = doc.createElement('genre')
    genre.setAttribute('authority', 'local')
    cit_type = citation.get_type_controlled_display().lower()
    genre.appendChild(doc.createTextNode(cit_type))
    mods.appendChild(genre)

    part = doc.createElement('part')
    mods.appendChild(part)

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

    publishers = citation.acrelation_set.filter(type_controlled__in=['PU'])
    for pub in publishers:
        publisher = doc.createElement('publisher')
        publisher.appendChild(doc.createTextNode(pub.authority.name))
        origin_info.appendChild(publisher)

    start_page = str(citation.part_details.page_begin)
    end_page = str(citation.part_details.page_end)

    if start_page or end_page:
        extent = doc.createElement('extent')
        extent.setAttribute('unit', 'page')
        part.appendChild(extent)
        if start_page:
            start = doc.createElement('start')
            start.appendChild(doc.createTextNode(start_page))
            extent.appendChild(start)
        if end_page:
            end = doc.createElement('end')
            end.appendChild(doc.createTextNode(end_page))
            extent.appendChild(end)

    return doc.toprettyxml(indent="    ", encoding="utf-8")

def get_volume(citation):
    if citation.part_details.volume:
        return citation.part_details.volume
    elif citation.part_details.volume_free_text:
        return citation.part_details.volume_free_text
    return ''

def get_issue(citation):
    issue = ''
    if citation.part_details.issue_begin:
        issue = str(citation.part_details.issue_begin)
    if citation.part_details.issue_end:
        issue += " - " + str(citation.part_details.issue_end)

    return issue
