from isisdata.models import *
from isisdata.templatetags.app_filters import *

def get_printlike_citation(id):
    citation = Citation.objects.get(pk=id)

    # ASSEMBLE FORMATTED COMPONENTS

    # contribs
    formatted_citation = _format_contributors(citation)

    # title
    formatted_citation = formatted_citation + ' ' + _format_title(citation) + ' '

    # publisher_or_periodical
    formatted_citation = formatted_citation + _format_publisher_or_periodical(citation)

    # date
    formatted_publisher_or_periodical = _format_publisher_or_periodical(citation)
    formatted_citation = formatted_citation + _format_date(citation, formatted_publisher_or_periodical)

    # pages_or_isbn
    formatted_citation = formatted_citation + _format_pages_or_isbn(citation)

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
    contribs = [acrel.authority.name for acrel in filter(lambda rel: rel.authority and rel.authority.name, contrib_acrelations)]

    if not contribs:
        return ''
    
    formatted_contributors = _build_name_last_first_html(contribs[0])
    if len(contribs) == 2:
        formatted_contributors = formatted_contributors + 'and ' + _build_name_first_last_html(contribs[1])
    elif len(contribs) == 3:
        formatted_contributors = formatted_contributors + ', ' + _build_name_first_last_html(contribs[1]) + ', and ' + _build_name_first_last_html(contribs[2])
    elif len(contribs) > 3:
        formatted_contributors = formatted_contributors + ', ' + _build_name_first_last_html(contribs[1]) + ', ' + _build_name_first_last_html(contribs[2]) + ', et al.'

    formatted_contributors = formatted_contributors + ('.' if formatted_contributors[-1] != '.' else '')

    return formatted_contributors

def _build_name_last_first_html(contrib):
    if "," in contrib:
        return '<span style="font-variant: small-caps;">' + contrib.split(',')[0] + '</span>, ' + contrib.split(',')[1]
    if " " in contrib:
        return '<span style="font-variant: small-caps;">' + contrib.split(' ')[1] + '</span>, ' + contrib.split(' ')[0]  
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

    if citation.type_controlled == Citation.BOOK: 
        publishers = ACRelation.objects.filter(citation=citation, type_controlled=ACRelation.PUBLISHER, public=True)
        return publishers.first().authority.name + ',' if publishers and publishers.first().authority else ''
    
    if citation.type_controlled == Citation.CHAPTER:
        containing_citation = CCRelation.objects.filter(object_id=citation.id, type_controlled=CCRelation.INCLUDES_CHAPTER, subject__public=True, public=True)
        formatted_publisher_or_periodical = ' In <i>' + containing_citation.first().subject.title + '</i>' if containing_citation else ''
        containing_citation_editor = containing_citation.first().subject.get_all_contributors[0].authority if containing_citation and containing_citation.first().subject.get_all_contributors else None
        formatted_publisher_or_periodical = formatted_publisher_or_periodical + (', edited by <span style="font-variant: small-caps;">' + containing_citation_editor.name + '</span>' if containing_citation_editor else '')
        return formatted_publisher_or_periodical
    
    if citation.type_controlled == Citation.THESIS:
        schools = ACRelation.objects.filter(citation=citation.id, type_controlled=ACRelation.SCHOOL, public=True)
        return 'Dissertation at ' + schools.first().authority.name if schools and schools.first().authority else ''
    
    return _format_periodicals(citation)

def _format_periodicals(citation):
    """
    formats volume number and issue numbers for periodicals, 
    accounting for the fact that some records have data in multiple fields describing volume and issue numbers
    """

    periodicals = ACRelation.objects.filter(citation=citation, type_controlled=ACRelation.PERIODICAL, public=True)
    if not periodicals:
        return ''
    
    formatted_publisher_or_periodical = '<i>' + periodicals.first().authority.name + '</i> ' if periodicals.first().authority else ''
    if citation.part_details:
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
    return ('(' if formatted_publisher_or_periodical and formatted_publisher_or_periodical[-1] == ' ' else ' (') + date.strftime('%Y') + ')'

def _format_pages_or_isbn(citation):
    isbn = None
    if citation.linkeddata_public:     
        isbn = next((linked_datum for linked_datum in citation.linkeddata_public if linked_datum.type_controlled.name == 'ISBN'), None)
    formatted_pages_or_isbn = '' 
    if citation.type_controlled == Citation.BOOK:
        if isbn:
            formatted_pages_or_isbn = formatted_pages_or_isbn + ' <span style="text-variant: small-caps;">ISBN</span>:' + isbn.universal_resource_name + '.'
    elif citation.type_controlled == Citation.THESIS:
        formatted_pages_or_isbn = '.'
    else:
        preamble = (', ' if citation.type_controlled == Citation.CHAPTER else ': ')
        if citation.part_details and citation.part_details.pages_free_text:
            formatted_pages_or_isbn = formatted_pages_or_isbn + preamble + citation.part_details.pages_free_text + '.'
        elif citation.part_details and citation.part_details.page_begin:
            formatted_pages_or_isbn = formatted_pages_or_isbn + preamble + str(citation.part_details.page_begin) + '.'
            if citation.part_details.page_end:
                formatted_pages_or_isbn = formatted_pages_or_isbn[:-1] + '-' + str(citation.part_details.page_end) + formatted_pages_or_isbn[-1:]

    return formatted_pages_or_isbn