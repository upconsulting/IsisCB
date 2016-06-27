from django import template
from django.utils.safestring import SafeText

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
    title = obj.title
    if not title:
        for relation in obj.ccrelations:
            if relation.type_controlled in [CCRelation.REVIEW_OF]:
                return u'Review: %s' % relation.citation.title
    return title


@register.filter(name='get_authors_editors')
def get_authors_editors(obj):
    return ', '.join([getattr(relation.authority, 'name', 'missing') + ' ('+  relation.get_type_controlled_display() + ')' for relation in obj.acrelations
                if relation.type_controlled in [ACRelation.AUTHOR, ACRelation.EDITOR]])


@register.filter(name='get_citation_pubdate')
def get_citation_pubdate(obj):
    date = getattr(obj, 'publication_date', None)
    if not date:
        return 'missing'
    return date.isoformat()[:4]


@register.filter(name='get_citation_periodical')
def get_citation_periodical(obj):
    return ', '.join(['%s (%s)' % (getattr(relation.authority, 'name', ''), relation.get_type_controlled_display()) for relation in obj.acrelations
        if relation.type_controlled in [ACRelation.PUBLISHER, ACRelation.PERIODICAL, ACRelation.BOOK_SERIES]])
