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
        formatted_citation = formatted_contributors
    else:
        formatted_citation = formatted_contributors + '.'

    # title
    formatted_citation = formatted_citation + ' ' + formatted_title + ' '

    # publisher_or_periodical
    formatted_citation = formatted_citation + formatted_publisher_or_periodical

    # date
    formatted_citation = formatted_citation + formatted_date

    # pages_or_isbn
    formatted_citation = formatted_citation + formatted_pages_or_isbn

    return mark_safe(formatted_citation)

def _format_contributors(citation): # formats list of contributor names depending on the number of contributors in the last; formats all surnames in smallcaps
    test = ['', '', '']
    print('yyyyyy')
    print(len(test))
    contrib_acrelations = citation.get_all_contributors
    contribs = []
    if contrib_acrelations:
        for contrib_acrelation in contrib_acrelations:
            if contrib_acrelation.authority.name:
                contribs.append(contrib_acrelation.authority.name)
                
    formatted_contributors = ''
    if contribs:
        formatted_contributors = _build_name_last_first_html(contribs[0]) + '.' # if there's just 1 contributor: "LASTNAME, Firstname"
    
        if len(contribs) == 2: # if 2 contributors: "LASTNAME1, Firstname1 and Firstname2 LASTNAME2."
            formatted_contributors = formatted_contributors + 'and ' + _build_name_first_last_html(contribs[1]) + '.'
        elif len(contribs) == 3: # if 2 contributors: "LASTNAME1, Firstname1, Firstname2 LASTNAME2, and Firstname3 LASTNAME3."
            formatted_contributors = formatted_contributors + ', ' + _build_name_first_last_html(contribs[1]) + ', and ' + _build_name_first_last_html(contribs[2]) + '.'
        elif len(contribs) > 3: # if more than 3 contributors: "LASTNAME1, Firstname1, Firstname2 LASTNAME2, Firstname3 LASTNAME3, et al."
            formatted_contributors = formatted_contributors + ', ' + _build_name_first_last_html(contribs[1]) + ', ' + _build_name_first_last_html(contribs[2]) + ', et al.'
    
    return formatted_contributors

def _build_name_last_first_html(contrib):
    if "," in contrib:
        return '<span style="font-variant: small-caps;">' + contrib.split(',')[0] + '</span>, ' + contrib.split(',')[1]  
    elif " " in contrib:
        return '<span style="font-variant: small-caps;">' + contrib.split(' ')[1] + '</span>, ' + contrib.split(' ')[0]
    else:
        return '<span style="font-variant: small-caps;">' + contrib + '</span>'
def _build_name_first_last_html(contrib):
    if "," in contrib:
        return contrib.split(',')[1] + ' <span style="font-variant: small-caps;">' + contrib.split(',')[0] + '</span>'
    elif " " in contrib: 
        return contrib.split(' ')[0] + ' <span style="font-variant: small-caps;">' + contrib.split(' ')[1] + '</span>'
    else:
        return '<span style="font-variant: small-caps;">' + contrib + '</span>'
    
def _format_title(citation):
    title = get_title(citation)
    formatted_title = ''
    if citation.type_controlled == Citation.BOOK: # if it's a book, italicize the title
        formatted_title = '<i>' + title + '</i>.'
    elif citation.type_controlled == Citation.REVIEW or citation.type_controlled == Citation.ESSAY_REVIEW:
        formatted_title = title + '.'
    else:
        formatted_title = '"' + title + '."'
    
    return formatted_title

def _format_publisher_or_periodical(citation):
    publishers = ACRelation.objects.filter(citation=citation, type_controlled=ACRelation.PUBLISHER).filter(public=True)
    containing_citation = CCRelation.objects.filter(object_id=citation.id, type_controlled=CCRelation.INCLUDES_CHAPTER, subject__public=True).filter(public=True)
    periodicals = ACRelation.objects.filter(citation=citation, type_controlled=ACRelation.PERIODICAL).filter(public=True)
    formatted_publisher_or_periodical = ''
    if citation.type_controlled == Citation.BOOK and publishers: 
        formatted_publisher_or_periodical = publishers[0].authority.name + ','
    elif citation.type_controlled == Citation.CHAPTER and containing_citation:
        formatted_publisher_or_periodical = ' In <i>' + containing_citation[0].subject.title + '</i>'
        containing_citation_editor = containing_citation[0].subject.get_all_contributors[0].authority if containing_citation[0].subject.get_all_contributors else None
        if containing_citation_editor:
            formatted_publisher_or_periodical = formatted_publisher_or_periodical + ', edited by <span style="font-variant: small-caps;">' + containing_citation_editor.name
    elif citation.type_controlled == Citation.THESIS:
        schools = ACRelation.objects.filter(citation=citation.id, type_controlled=ACRelation.SCHOOL).filter(public=True)
        if schools:
            formatted_publisher_or_periodical = 'Dissertation at ' + schools[0].authority.name
    elif periodicals:
        formatted_publisher_or_periodical = '<i>' + periodicals[0].authority.name + '</i> '
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
        if citation.type_controlled == Citation.BOOK: # if it's a book, terminate the publication year with a period
            formatted_date = ' ' + date.strftime('%Y') + '.'
        else: # otherwise, wrap the publication year in parentheses
            formatted_date = ('(' if formatted_publisher_or_periodical and formatted_publisher_or_periodical[-1] is ' ' else ' (') + date.strftime('%Y') + ')'

    return formatted_date

def _format_pages_or_isbn(citation):
    formatted_pages_or_isbn = ''
    isbn = None
    if citation.linkeddata_public:            
        isbn = [linked_datum if linked_datum.type_controlled == 'ISBN' else None for linked_datum in citation.linkeddata_public][0]
        
    if citation.type_controlled == Citation.BOOK:
        if isbn:
            formatted_pages_or_isbn = formatted_pages_or_isbn + ' <span style="text-variant: small-caps;">ISBN</span>:' + isbn.universal_resource_name + '.'
    elif citation.type_controlled == Citation.THESIS:
        formatted_pages_or_isbn = '.'
    else:
        formatted_pages_or_isbn = (', ' if citation.type_controlled is 'CH' else ': ')
        if citation.part_details.pages_free_text:
            formatted_pages_or_isbn = formatted_pages_or_isbn + citation.part_details.pages_free_text
        elif citation.part_details.page_begin:
            formatted_pages_or_isbn = formatted_pages_or_isbn + citation.part_details.page_begin
            if citation.part_details.page_end:
                formatted_pages_or_isbn = formatted_pages_or_isbn + citation.part_details.page_end
        formatted_pages_or_isbn = formatted_pages_or_isbn + '.'

    return formatted_pages_or_isbn