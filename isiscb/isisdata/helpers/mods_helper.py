

def get_type(citation_type):
    type_dict = {}
    type_dict['BO'] = 'book'
    type_dict['AR'] = 'article'
    type_dict['CH'] = 'bookSection'
    type_dict['RE'] = 'journalArticle'
    type_dict['ES'] = 'journalArticle'
    type_dict['TH'] = 'thesis'
    type_dict['EV'] = 'document'
    type_dict['PR'] = 'presentation'
    type_dict['IN'] = 'document'
    type_dict['WE'] = 'document'
    type_dict['AP'] = 'computerProgram'

    return type_dict.get(citation_type, 'document')

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
