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

# formats list of contributor names depending on the number of contributors in the last; formats all surnames in smallcaps
def _format_contributors(citation): 
    """
     Function to format the list of contributors, in the following way:
     - one author: LASTNAME, Firstname.
     - two authors: LASTNAME1, Firstname1 and Firstname2 LASTNAME2.
     - three authors: LASTNAME1, Firstname1, Firstname2 LASTNAME2, and Firstname3 LASTNAME3.
     - more than three authors: LASTNAME1, Firstname1, Firstname2 LASTNAME2, Firstname3 LASTNAME3, et al.
    """
    contrib_acrelations = citation.get_all_contributors
    contribs = [acrel.authority.name for acrel in filter(lambda rel: rel.authority.name, contrib_acrelations)]

    formatted_contributors = ''
    if contribs:
        formatted_contributors = _build_name_last_first_html(contribs[0])
        if len(contribs) == 1:
            formatted_contributors = formatted_contributors + '.'
        elif len(contribs) == 2:
            formatted_contributors = formatted_contributors + 'and ' + _build_name_first_last_html(contribs[1]) + '.'
        elif len(contribs) == 3:
            formatted_contributors = formatted_contributors + ', ' + _build_name_first_last_html(contribs[1]) + ', and ' + _build_name_first_last_html(contribs[2]) + '.'
        elif len(contribs) > 3:
            formatted_contributors = formatted_contributors + ', ' + _build_name_first_last_html(contribs[1]) + ', ' + _build_name_first_last_html(contribs[2]) + ', et al.'
    
    return formatted_contributors

def _build_name_last_first_html(contrib):
    if " " in contrib:
        return '<span style="font-variant: small-caps;">' + contrib.split(' ')[1] + '</span>, ' + contrib.split(' ')[0]
    if "," in contrib:
        return '<span style="font-variant: small-caps;">' + contrib.split(',')[0] + '</span>, ' + contrib.split(',')[1]  
    return '<span style="font-variant: small-caps;">' + contrib + '</span>'
    
def _build_name_first_last_html(contrib):
    if " " in contrib: 
        return contrib.split(' ')[0] + ' <span style="font-variant: small-caps;">' + contrib.split(' ')[1] + '</span>'
    if "," in contrib:
        return contrib.split(',')[1] + ' <span style="font-variant: small-caps;">' + contrib.split(',')[0] + '</span>'
    return '<span style="font-variant: small-caps;">' + contrib + '</span>'
    
def _format_title(citation):
    title = get_title(citation)
    # if it's a book, italicize the title
    if citation.type_controlled == Citation.BOOK:
        return '<i>' + title + '</i>.'
    if citation.type_controlled == Citation.REVIEW or citation.type_controlled == Citation.ESSAY_REVIEW:
        return title + '.'
    return '"' + title + '."'

def _format_publisher_or_periodical(citation):
    """
    Function to format the publisher (for books), container book (for chapters), or hosting periodical (for journal articles, essay reviews, book reviews)
    - for books: "PublisherName,"
    - for chapters: " In TitleOfBookContainingTheChapter, edited by 
    """
    formatted_publisher_or_periodical = ''

    publishers = ACRelation.objects.filter(citation=citation, type_controlled=ACRelation.PUBLISHER).filter(public=True)
    if citation.type_controlled == Citation.BOOK and publishers: 
        return publishers[0].authority.name + ','
    
    containing_citation = CCRelation.objects.filter(object_id=citation.id, type_controlled=CCRelation.INCLUDES_CHAPTER, subject__public=True).filter(public=True)
    if citation.type_controlled == Citation.CHAPTER and containing_citation:
        formatted_publisher_or_periodical = ' In <i>' + containing_citation[0].subject.title + '</i>'
        containing_citation_editor = containing_citation[0].subject.get_all_contributors[0].authority if containing_citation[0].subject.get_all_contributors else None
        if containing_citation_editor:
            formatted_publisher_or_periodical = formatted_publisher_or_periodical + ', edited by <span style="font-variant: small-caps;">' + containing_citation_editor.name + '</span>'
        return formatted_publisher_or_periodical
    
    if citation.type_controlled == Citation.THESIS:
        schools = ACRelation.objects.filter(citation=citation.id, type_controlled=ACRelation.SCHOOL).filter(public=True)
        return 'Dissertation at ' + schools[0].authority.name if schools else ''
    
    periodicals = ACRelation.objects.filter(citation=citation, type_controlled=ACRelation.PERIODICAL).filter(public=True)
    if periodicals:
        return _format_periodicals(citation, periodicals)

def _format_periodicals(citation, periodicals):
    """
    formats volume number and issue numbers for periodicals, 
    accounting for the fact that some records have data in multiple fields describing volume and issue numbers
    """
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
    if not date:
        return ''
    # if it's a book, terminate the publication year with a period
    if citation.type_controlled == Citation.BOOK: 
            return ' ' + date.strftime('%Y') + '.'
    # otherwise, wrap the publication year in parentheses
    return ('(' if formatted_publisher_or_periodical and formatted_publisher_or_periodical[-1] is ' ' else ' (') + date.strftime('%Y') + ')'

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