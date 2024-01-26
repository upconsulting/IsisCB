from isisdata.models import *
from isisdata.templatetags.app_filters import *

def get_printlike_citation(id):
    citation = Citation.objects.get(pk=id)
    formatted_citation = ''

    formatted_contributors = _format_contributors(citation)
    formatted_title = _format_title(citation)
    formatted_publisher_or_periodical = _format_publisher_or_periodical(citation)
    formatted_date = _format_date(citation, formatted_publisher_or_periodical)
    formatted_pages_or_isbn = _format_pages_or_isbn(citation)

    # ASSEMBLE FORMATTED COMPONENTS
    # contribs
    if formatted_contributors and formatted_contributors[-1] == '.':
        formatted_citation = formatted_citation + formatted_contributors
    else:
        formatted_citation = formatted_citation + formatted_contributors + '.'
    # title
    formatted_citation = formatted_citation + ' ' + formatted_title + ' '

    # publisher_or_periodical
    formatted_citation = formatted_citation + formatted_publisher_or_periodical

    # date
    formatted_citation = formatted_citation + formatted_date

    # pages_or_isbn
    formatted_citation = formatted_citation + formatted_pages_or_isbn

    return mark_safe(formatted_citation)

def _format_contributors(citation):
    contrib_acrelations = citation.get_all_contributors
    contribs = [contrib_acrelation.authority.name for contrib_acrelation in contrib_acrelations]
    formatted_contributors = ''
    if contribs:
        # citations have different numbers of contributors (authors/editors); most citations have 1 contributor, some 2, 3, or more
        # contributor lists need to be formatted differently depending on how many contributors there are
        for index, contrib in enumerate(contribs):
            if index is 0: # formatting the first contributor in the list
                # formatting the name as Surname, Given-name with surname in small-caps, or just mononym in small caps for contributors (e.g. Aristotle) who have mononyms
                formatted_contributors = formatted_contributors + '<span style="font-variant: small-caps;">' + (contrib.split(',')[0] + '</span>,' + contrib.split(',')[1] if ',' in contrib else contrib + '</span>')
            elif (index is 1 or index is 2) and len(contribs) == index+1: # formatting the 2nd or 3rd contributor that is also the last in the list
                # append " and Given-name Surname" with surname in small-caps to formatted list of contributors
                formatted_contributors = formatted_contributors + ' and' + contrib.split(',')[1] + ' <span style="font-variant: small-caps;">' + contrib.split(',')[0] + '</span>.'
            elif index is 1 and len(contribs) > 2: # formatting the 2nd contributor to a list that has 3 or more contribs
                # append ", Given-name Surname" with surname in small-caps to formatted list of contributors
                formatted_contributors = formatted_contributors + ', ' + contrib.split(',')[1] + ' <span style="font-variant: small-caps;">' + contrib.split(',')[0] + '</span>,'
            elif index is 2 and len(contribs) > 3: # formatting the 3rd contributor to a list that has 4 or more contribs
                # append ", Given-name Surname, et al." with surname in small-caps to formatted list of contributors
                formatted_contributors = formatted_contributors + contrib.split(',')[1] + ' <span style="font-variant: small-caps;">' + contrib.split(',')[0] + '</span>, et al.'
            elif index > 2:
                break
    
    return formatted_contributors

def _format_title(citation):
    title = get_title(citation)
    formatted_title = ''
    if citation.type_controlled == Citation.BOOK:
        formatted_title = formatted_title + '<i>' + title + '</i>.'
    elif citation.type_controlled == Citation.REVIEW or citation.type_controlled == Citation.ESSAY_REVIEW:
        formatted_title = formatted_title + title + '.'
    else:
        formatted_title = formatted_title + '"' + title + '."'
    
    return formatted_title

def _format_publisher_or_periodical(citation):
    publishers = ACRelation.objects.filter(citation=citation, type_controlled=ACRelation.PUBLISHER).filter(public=True)
    containing_citation = CCRelation.objects.filter(object_id=citation.id, type_controlled=CCRelation.INCLUDES_CHAPTER, subject__public=True).filter(public=True)
    periodicals = ACRelation.objects.filter(citation=citation, type_controlled=ACRelation.PERIODICAL).filter(public=True)
    formatted_publisher_or_periodical = ''
    if citation.type_controlled == Citation.BOOK and publishers:
        formatted_publisher_or_periodical = formatted_publisher_or_periodical + publishers[0].authority.name + ','
    elif citation.type_controlled == Citation.CHAPTER and containing_citation:
        formatted_publisher_or_periodical = formatted_publisher_or_periodical + ' In <i>' + containing_citation[0].subject.title + '</i>'
        containing_citation_editor = containing_citation[0].subject.get_all_contributors[0].authority if containing_citation[0].subject.get_all_contributors else None
        if containing_citation_editor:
            formatted_publisher_or_periodical = formatted_publisher_or_periodical + ', edited by <span style="font-variant: small-caps;">' + containing_citation_editor.name
    elif citation.type_controlled == Citation.THESIS:
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

    return formatted_publisher_or_periodical

def _format_date(citation, formatted_publisher_or_periodical):
    date = citation.publication_date
    formatted_date = ''
    if date:
        if citation.type_controlled == Citation.BOOK:
            formatted_date = formatted_date + ' ' + date.strftime('%Y') + '.'
        else:
            formatted_date = formatted_date + ('(' if formatted_publisher_or_periodical and formatted_publisher_or_periodical[-1] is ' ' else ' (') + date.strftime('%Y') + ')'

    return formatted_date

def _format_pages_or_isbn(citation):
    formatted_pages_or_isbn = ''
    # linked_data = citation.linkeddata_public
    isbn = None
    if citation.linkeddata_public:            
        isbn = [linked_datum if linked_datum.type_controlled == 'ISBN' else None for linked_datum in citation.linkeddata_public][0]
        
    if citation.type_controlled == Citation.BOOK:
        if isbn:
            formatted_pages_or_isbn = formatted_pages_or_isbn + ' <span style="text-variant: small-caps;">ISBN</span>:' + isbn.universal_resource_name + '.'
    elif citation.type_controlled == Citation.THESIS:
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

    return formatted_pages_or_isbn