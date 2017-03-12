from django import template
from isisdata.models import *

register = template.Library()

@register.filter
def roles(userid):
    return IsisCBRole.objects.filter(users__pk=userid)

@register.filter
def print_roles(roles):
    return ", ".join(map((lambda role: role.name), roles))

@register.filter
def needs_view_rule(crud_rules):
    can_read = False
    for rule in crud_rules:
        if rule.crud_action == CRUDRule.VIEW:
            can_read = True

    if len(crud_rules) > 0 and not can_read:
        return True

    return False

@register.filter
def create_perm_tuple(fieldname, id):
    return (fieldname, id)

@register.filter
def get_warnings_column_count_citation(instance):
    nr_of_warnings = 0
    if not instance.public:
        nr_of_warnings += 1
    if not are_related_objects_for_citation_public(instance):
        nr_of_warnings += 1
    if is_public_inconsistent(instance):
        nr_of_warnings += 1
    if does_chapter_miss_book(instance):
        nr_of_warnings += 1
    if reviewed_book_missing(instance):
        nr_of_warnings += 1
    if is_periodical_missing(instance):
        nr_of_warnings += 1

    if nr_of_warnings == 0:
        return 12
    return 12/nr_of_warnings

@register.filter
def does_chapter_miss_book(instance):
    if instance.type_controlled == Citation.CHAPTER:
        includes_chapter = instance.ccrelations.filter(type_controlled=CCRelation.INCLUDES_CHAPTER);
        if not includes_chapter:
            return True;
    return False;

@register.filter
def reviewed_book_missing(instance):
    if instance.type_controlled == Citation.REVIEW:
        reviews = instance.ccrelations.filter(type_controlled__in=[CCRelation.REVIEWED_BY, CCRelation.REVIEW_OF])
        if not reviews:
            return True;
    return False;

@register.filter
def is_periodical_missing(instance):
    if instance.type_controlled in [Citation.REVIEW, Citation.ARTICLE]:
        has_periodical = instance.acrelations.filter(type_controlled=ACRelation.PERIODICAL)
        if not has_periodical:
            return True
    return False

@register.filter
def get_warnings_column_count_authority(instance):
    nr_of_warnings = 0
    if not instance.public:
        nr_of_warnings += 1
    if not are_related_objects_for_authority_public(instance):
        nr_of_warnings += 1
    if is_public_inconsistent(instance):
        nr_of_warnings += 1
    print nr_of_warnings
    if nr_of_warnings == 0:
        return 0
    return 12/nr_of_warnings

@register.filter
def is_public_inconsistent(instance):
    if instance.public and instance.record_status_value != CuratedMixin.ACTIVE:
        return True
    if not instance.public and instance.record_status_value == CuratedMixin.ACTIVE:
        return True
    return False

@register.filter
def are_related_objects_for_citation_public(citation):
    for acrel in citation.acrelations:
        if not acrel.public:
            return False
        if not getattr(acrel.authority, 'public', None):
            return False

    for ccrel in citation.ccrelations:
        if not ccrel.public:
            return False
        if not ccrel.object.public:
            return False

    for attr in citation.attributes.all():
        if not attr.public:
            return False

    return True

@register.filter
def get_authorities(acrelations):
    authorities = []
    for acrel in acrelations:
        authorities.append(acrel.authority)
    return authorities

@register.filter
def get_citations(citation, ccrelations):
    citations = []
    for ccrel in ccrelations:
        if ccrel.subject == citation:
            citations.append(ccrel.object)
        else:
            citations.append(ccrel.subject)
    return citations

@register.filter
def are_related_authorities_public(acrelations, authorities):
    for acrel in acrelations:
        if not acrel.public:
            return False
    for authority in authorities:
        if not authority.public:
            return False
    return True

@register.filter
def are_related_citations_public(ccrelations, citations):
    for ccrel in ccrelations:
        if not ccrel.public:
            return False
    for citation in citations:
        if not citation.public:
            return False
    return True

@register.filter
def are_attributes_public(attributes):
    for attr in attributes:
        if not attr.public:
            return False
    return True

@register.filter
def are_linked_books_public(citation_id, citations):
    for citation in citations:
        if citation.type_controlled == Citation.BOOK:
            if not citation.public:
                return False

            query = (Q(subject_id=citation_id) & Q(object_id=citation.id)) | (Q(object_id=citation_id) & Q(subject_id=citation.id))
            ccrels = CCRelation.objects.filter(query)

            for ccrel in ccrels:
                if not ccrel.public:
                    return False

    return True

@register.filter
def are_linked_journals_public(citation_id, authorities):
    for authority in authorities:
        if authority.type_controlled == Authority.SERIAL_PUBLICATION:
            if not authority.public:
                return False

            query = Q(authority_id=authority.id) & Q(citation_id=citation_id)
            acrels = ACRelation.objects.filter(query)
            for acrel in acrels:
                if not acrel.public:
                    return False

    return True

@register.filter
def are_related_objects_for_authority_public(authority):
    if ACRelation.objects.filter(authority__pk=authority.pk).filter(public=False):
        return False
    if ACRelation.objects.filter(authority__pk=authority.pk).filter(citation__public=False):
        return False

    for aarel in authority.aarelations:
        if not aarel.public:
            return False
        if not aarel.object.public:
            return False

    for attr in authority.attributes.all():
        if not attr.public:
            return False

    return True

@register.filter
def get_dataset_name(ds_id):
    if not ds_id:
        return "No Dataset"
    try:
        return Dataset.objects.get(pk=ds_id).name
    except ValueError:
        return 'Error, please update role.'
