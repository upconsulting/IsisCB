from __future__ import unicode_literals
from django import template
from isisdata.models import *
from dateutil.relativedelta import relativedelta
from isisdata.templatetags.app_filters import *

register = template.Library()

# this method also exists in app_filters; need to be consolidated
@register.filter
def get_uri(entry, tenant=None):
    if to_class_name(entry) == 'Authority':
        return (settings.URI_PREFIX if not tenant else settings.URI_HOST + settings.PORTAL_PREFIX + '/' + tenant + "/") + "authority/" + entry.id
    if to_class_name(entry) == 'Citation':
        return (settings.URI_PREFIX if not tenant else settings.URI_HOST + settings.PORTAL_PREFIX + '/' + tenant + "/") + "citation/" + entry.id
    return ""

@register.filter
def to_class_name(value):
    return value.__class__.__name__

@register.filter
def get_iso_date_string(date):
    return date.isoformat()

@register.filter
def add_css_placeholder(field, css_placeholder):
    parts = css_placeholder.split(';')
    placeholder = parts[1] if len(parts) >= 2 else ''
    css = parts[0]
    return field.as_widget(attrs={"placeholder": placeholder, "class": css})

@register.filter
def add_popover(field, css_placeholder_text):
    parts = css_placeholder_text.split(';')
    placeholder = parts[1] if len(parts) >= 2 else ''
    text = parts[2] if len(parts) >= 3 else ''
    orientation = parts[3] if len(parts) >= 4 else 'right'
    css = parts[0]

    return field.as_widget(attrs={"class": css, "placeholder": placeholder, \
                    "data-toggle": "popover", "data-trigger":"hover", \
                    "data-placement": orientation, "data-content": text})

@register.filter(name='field_type')
def field_type(field):
    return field.field.widget.__class__.__name__

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def is_external_tenant(record, tenant):
    if (not record.owning_tenant and tenant) or (record.owning_tenant and not tenant):
        return True    

    return False if record.owning_tenant.id is tenant.id else True

@register.filter
def get_tenant(id):
    if id:
        return Tenant.objects.get(pk=id)
    return ""

@register.filter
def get_print_formatted_citation(id):
    citation = Citation.objects.get(pk=id)
    formatted_citation = ''

    # format contributors
    contrib_acrelations = citation.get_all_contributors
    contribs = [contrib_acrelation.authority.name for contrib_acrelation in contrib_acrelations]
    formatted_contribs = ''
    if len(contribs):
        for index, contrib in enumerate(contribs):
            if index is 0:
                formatted_contribs = formatted_contribs + '<span style="font-variant: small-caps;">' + (contrib.split(',')[0] + '</span>,' + contrib.split(',')[1] if ',' in contrib else contrib + '</span>')
            elif (index is 1 or index is 2) and len(contribs) == index+1:
                formatted_contribs = formatted_contribs + ' and' + contrib.split(',')[1] + ' <span style="font-variant: small-caps;">' + contrib.split(',')[0] + '</span>.'
            elif index is 1 and len(contribs) > 2:
                formatted_contribs = formatted_contribs + ', ' + contrib.split(',')[1] + '<span style="font-variant: small-caps;">' + contrib.split(',')[0] + '</span>,'
            elif index is 2 and len(contribs) > 3:
                formatted_contribs = formatted_contribs + contrib.split(',')[1] + '<span style="font-variant: small-caps;">' + contrib.split(',')[0] + '</span>, el al.'

    # format title
    title = get_title(citation)
    formatted_title = ''
    if citation.type_controlled == 'BO':
        formatted_title = formatted_title + '<i>' + title + '</i>.'
    elif citation.type_controlled == 'RE' or citation.type_controlled == 'ES':
        formatted_title = formatted_title + title + '.'
    else:
        formatted_title = formatted_title + '"' + title + '."'
    
    # format publisher_or_periodical
    publishers = ACRelation.objects.filter(citation=citation, type_controlled=ACRelation.PUBLISHER).filter(public=True)
    containing_citation = CCRelation.objects.filter(object_id=citation.id, type_controlled=CCRelation.INCLUDES_CHAPTER, subject__public=True).filter(public=True)
    periodicals = ACRelation.objects.filter(citation=citation, type_controlled=ACRelation.PERIODICAL).filter(public=True)
    formatted_publisher_or_periodical = ''
    if citation.type_controlled == 'BO' and publishers:
        formatted_publisher_or_periodical = formatted_publisher_or_periodical + publishers[0].authority.name + ','
    elif citation.type_controlled == 'CH' and containing_citation:
        formatted_publisher_or_periodical = formatted_publisher_or_periodical + ' In <i>' + containing_citation[0].subject.title + '</i>'
        containing_citation_editor = containing_citation[0].subject.get_all_contributors[0].authority if containing_citation[0].subject.get_all_contributors else None
        if containing_citation_editor:
            formatted_publisher_or_periodical = formatted_publisher_or_periodical + ', edited by <span style="font-variant: small-caps;">' + containing_citation_editor.name
    elif citation.type_controlled == 'TH':
        schools = ACRelation.objects.filter(citation=citation.id, type_controlled=ACRelation.SCHOOL).filter(public=True)
        if schools:
            formatted_publisher_or_periodical = formatted_publisher_or_periodical + 'Dissertation at ' + schools[0].authority.name
    elif periodicals:
        formatted_publisher_or_periodical = formatted_publisher_or_periodical + '<i>' + periodicals[0].authority.name + '</i> '
        if citation.part_details.volume:
            formatted_publisher_or_periodical = formatted_publisher_or_periodical + citation.part_details.volume
        elif citation.part_details.volume_free_text:
            formatted_publisher_or_periodical = formatted_publisher_or_periodical + citation.part_details.volume_free_text
        elif citation.part_details.volume_begin:
            formatted_publisher_or_periodical = formatted_publisher_or_periodical + str(citation.part_details.volume_begin)
            if citation.part_details.volume_end:
                formatted_publisher_or_periodical = formatted_publisher_or_periodical + '-' + str(citation.part_details.volume_end)
        if citation.part_details.issue_free_text:
            formatted_publisher_or_periodical = formatted_publisher_or_periodical + ', no. ' + citation.part_details.issue_free_text
        elif citation.part_details.issue_begin:
            formatted_publisher_or_periodical = formatted_publisher_or_periodical + ', no. ' + str(citation.part_details.issue_begin)
            if citation.part_details.issue_end:
                formatted_publisher_or_periodical = formatted_publisher_or_periodical + '-' + str(citation.part_details.issue_end)

    # format date
    date = citation.publication_date
    formatted_date = ''
    if date:
        if citation.type_controlled == 'BO':
            formatted_date = formatted_date + ' ' + date.strftime('%Y') + '.'
        else:
            formatted_date = formatted_date + ('(' if formatted_publisher_or_periodical and formatted_publisher_or_periodical[-1] is ' ' else ' (') + date.strftime('%Y') + ')'

    # format pages_or_isbn
    formatted_pages_or_isbn = ''
    # linked_data = citation.linkeddata_public
    isbn = None
    if citation.linkeddata_public:            
        isbn = [linked_datum if linked_datum.type_controlled == 'ISBN' else None for linked_datum in citation.linkeddata_public][0]
        
    if citation.type_controlled == 'BO':
        if isbn:
            formatted_pages_or_isbn = formatted_pages_or_isbn + ' <span style="text-variant: small-caps;">ISBN</span>:' + isbn.universal_resource_name + '.'
    elif citation.type_controlled == 'TH':
        formatted_pages_or_isbn = formatted_pages_or_isbn + '.'
    else:
        formatted_pages_or_isbn = formatted_pages_or_isbn + (', ' if citation.type_controlled is 'CH' else ': ')
        if citation.part_details.pages_free_text:
            formatted_pages_or_isbn = formatted_pages_or_isbn + citation.part_details.pages_free_text
        elif citation.part_details.page_begin:
            formatted_pages_or_isbn = formatted_pages_or_isbn + citation.part_details.page_begin
            if citation.part_details.page_end:
                formatted_pages_or_isbn = formatted_pages_or_isbn + citation.part_details.page_end
        formatted_pages_or_isbn = formatted_pages_or_isbn + '.'

    # ASSEMBLE FORMATTED COMPONENTS
    # contribs
    if formatted_contribs and formatted_contribs[-1] == '.':
        formatted_citation = formatted_citation + formatted_contribs
    else:
        formatted_citation = formatted_citation + formatted_contribs + '.'
    # title
    formatted_citation = formatted_citation + ' ' + formatted_title + ' '

    # publisher_or_periodical
    formatted_citation = formatted_citation + formatted_publisher_or_periodical

    # date
    formatted_citation = formatted_citation + formatted_date

    # pages_or_isbn
    formatted_citation = formatted_citation + formatted_pages_or_isbn

    return mark_safe(formatted_citation)