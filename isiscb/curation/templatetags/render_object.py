from django import template
from django.utils.safestring import SafeText
from django.db.models import Q

from isisdata.models import *

register = template.Library()


PUBLICATION_DATE = AttributeType.objects.get(name='PublicationDate').id


@register.filter(name='render_object')
def render_object(obj):
    model_name = obj.__class__.__name__
    # model_class = globals().get(model_name)
    elem = u'<div class="row">'
    if model_name == 'Citation':
        elem += '<span class="label label-primary">' + obj.get_type_controlled_display() + '</span> '
        elem += obj.title
        elem += '<span class="text-warning">'
        elem += ' by ' + ', '.join([getattr(relation.authority, 'name', 'missing') + ' ('+  relation.get_type_controlled_display() + ')' for relation in obj.acrelations
                    if relation.type_controlled in [ACRelation.AUTHOR, ACRelation.EDITOR]])


        elem += '</span>'

        elem += '<dl class="dl-horizontal">'
        elem += '<dt>Publication date</dt>'
        elem += '<dd>' + getattr(obj.publication_date, 'isoformat', lambda: 'missing')() + '</dd>'

        for relation in obj.acrelations:
            if relation.type_controlled in [ACRelation.PUBLISHER, ACRelation.PERIODICAL, ACRelation.BOOK_SERIES]:
                elem += '<dt>' + relation.get_type_controlled_display() + '</dt>'
                elem += '<dd>' + getattr(relation.authority, 'name', 'missing') + '</dd>'

        elem += '</dl>'

    else:
        elem += obj.__unicode__()
    elem += u'</div>'

    return SafeText(elem)


@register.filter(name='get_citation_title')
def get_citation_title(obj):
    if not obj:
        return u'No linked citation'
    title = obj.title
    if not title:
        for relation in obj.ccrelations:
            if relation.type_controlled in [CCRelation.REVIEW_OF, CCRelation.REVIEWED_BY]:
                return u'Review: %s' % relation.subject.title if relation.subject.id != obj.id else relation.object.title
        return u'Untitled review'
    return title


@register.filter(name='get_publisher')
def get_publisher(obj):
    acrel = obj.acrelations.filter(type_controlled=ACRelation.PUBLISHER).first()
    if acrel:
        return acrel.authority
    return None

@register.filter(name='get_isbn')
def get_isbn(obj):
    return obj.linkeddata_entries.filter(type_controlled__name='ISBN').first()

@register.filter(name='get_doi')
def get_doi(obj):
    return obj.linkeddata_entries.filter(type_controlled__name='DOI').first()


@register.filter(name='get_authors_editors')
def get_authors_editors(obj):
    return ', '.join([getattr(relation.authority, 'name', 'missing') + ' ('+  relation.get_type_controlled_display() + ')' for relation in obj.acrelations
                if relation.type_controlled in [ACRelation.AUTHOR, ACRelation.EDITOR]])

@register.filter(name='get_authors_advisors')
def get_authors_advisors(obj):
    return ', '.join([getattr(relation.authority, 'name', 'missing') + ' ('+  relation.get_type_controlled_display() + ')' for relation in obj.acrelations
                if relation.type_controlled in [ACRelation.AUTHOR, ACRelation.ADVISOR]])


@register.filter(name='get_authors_editors_preloaded')
def get_authors_editors_preloaded(acrelations):
    return ', '.join([getattr(relation.authority, 'name', 'missing') + ' ('+  relation.get_type_controlled_display() + ')' for relation in acrelations
                if relation.type_controlled in [ACRelation.AUTHOR, ACRelation.EDITOR]])


@register.filter(name='get_citation_pubdate')
def get_citation_pubdate(obj):
    for attribute in obj.attributes.all():
        if attribute.type_controlled.name == 'PublicationDate':
            return attribute.value.get_child_class().__unicode__()

    date = getattr(obj, 'publication_date', None)
    return 'missing' if not date else date.isoformat()[:4]


@register.filter(name='get_citation_pubdate_fast')
def get_citation_pubdate_fast(obj):
    date = getattr(obj, 'publication_date', None)
    if not date:
        return 'missing'
    return date.isoformat()[:4]

@register.filter
def get_reviewed_books(citation):
    ccrelations = citation.ccrelations.filter(Q(type_controlled=CCRelation.REVIEW_OF, subject__id=citation.id))
    citations =  map(lambda x: x.object, ccrelations)

    ccrelations = citation.ccrelations.filter(Q(type_controlled=CCRelation.REVIEWED_BY, object__id=citation.id))
    citations = citations + map(lambda x: x.subject, ccrelations)

    return citations

@register.filter
def get_including_book(citation):
    ccrelations = citation.ccrelations.filter(Q(type_controlled=CCRelation.INCLUDES_CHAPTER, object__id=citation.id))
    citations =  map(lambda x: x.subject, ccrelations)

    return citations

@register.filter
def get_pub_title_and_year(citation):
    return u"{0}, ({1})".format(citation.title, getattr(citation, 'publication_date', "Date missing"))


@register.filter(name='get_citation_periodical')
def get_citation_periodical(obj):
    return ', '.join(['%s (%s)' % (getattr(relation.authority, 'name', ''), relation.get_type_controlled_display()) for relation in obj.acrelations
        if relation.type_controlled in [ACRelation.PUBLISHER, ACRelation.PERIODICAL, ACRelation.BOOK_SERIES]])

@register.filter
def get_school(obj):
    return ', '.join(['%s (%s)' % (getattr(relation.authority, 'name', ''), relation.get_type_controlled_display()) for relation in obj.acrelations
        if relation.type_controlled in [ACRelation.SCHOOL]])


@register.filter(name='get_date_attributes')
def get_date_attributes(obj):
    return SafeText(', '.join(['<span class="label label-success">%s</span> %s' % (attribute.type_controlled.name, attribute.value.display) for attribute in obj.attributes.all()]))
