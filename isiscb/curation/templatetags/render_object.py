from django import template
from django.utils.safestring import SafeText

from isisdata.models import *

register = template.Library()


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
