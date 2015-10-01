from django import template
from isisdata.models import *
from django.conf import settings
from django.utils.safestring import mark_safe

from urllib import quote
import codecs
import re

import bleach

register = template.Library()


@register.filter(name='to_class_name')
def to_class_name(value):
    return value.__class__.__name__


@register.filter(name='joinby')
def joinby(value, arg):
    if arg == None or not arg:
        return ''
    try:
        return arg.join(value)
    except:
        return arg


@register.filter
def get_authors(value):
    if value:
        return value.acrelation_set.filter(type_controlled__in=['AU', 'CO'])
    return value


# QUESTION: what URIs do we use?
@register.filter
def get_uri(entry):
    if to_class_name(entry) == 'Authority':
        return settings.URI_PREFIX + "authority/" + entry.id
    if to_class_name(entry) == 'Citation':
        return settings.URI_PREFIX + "citation/" + entry.id
    return ""


@register.filter
def get_title(citation):
    # if citation is not a review simply return title
    if not citation.type_controlled == 'RE':
        if not citation.title:
            return "Title missing"
        return citation.title

    # if citation is a review build title from reviewed citation
    reviewed_books = CCRelation.objects.filter(subject_id=citation.id, type_controlled='RO')

    # sometimes RO relationship is not specified then use inverse reviewed by
    book = None
    if not reviewed_books:
        reviewed_books = CCRelation.objects.filter(object_id=citation.id, type_controlled='RB')
        if reviewed_books:
            book = reviewed_books[0].subject
    else:
        book = reviewed_books[0].object

    if book == None:
        return "Review of unknown publication"

    return 'Review of "' + book.title + '"'


@register.filter
def get_pub_year(citation):
    dates = citation.attributes.filter(type_controlled__name='PublicationDate')
    if dates:
        return dates[0].value_freeform
    return ''


@register.filter
def remove_facet(url, arg):
    return url.replace(arg, "").replace("&&", "&")


@register.filter
def create_facet_string(facet, field):
    return 'selected_facets=' + field + ':' + quote(codecs.encode(facet,'utf-8'))


@register.filter
def set_page_to_one(path):
    return re.sub(r"page=[0-9]*", "page=1", path)


@register.filter
def get_dates(authority):
    return authority.attributes.filter(type_controlled__value_content_type__model__in=['datevalue', 'datetimevalue'])


@register.filter
def join_attributes(attrlist, concator):
    return concator.join(attr.value_freeform for attr in attrlist)

@register.filter
def get_contributors(citation):
    return citation.acrelation_set.filter(type_controlled__in=['AU', 'CO', 'ED'])


@register.filter
def contributor_as_string(acrelation):
    kwargs = {'name': acrelation.authority.name,
              'role': acrelation.get_type_controlled_display()}
    return u"{name} ({role})".format(**kwargs)


SAFE_TAGS = ['em', 'b', 'i', 'strong', 'a']
SAFE_ATTRS = {'a': ['href', 'rel']}


@register.filter
def bleach_safe(s):
    """
    Strip any tags and attributes not in SAFE_TAGS and SAFE_ATTRS, respectively,
    and yield a SafeString.

    This *should* remediate unclosed tags and other weirdness.
    """
    return mark_safe(bleach.clean(s,
                                  tags=SAFE_TAGS, # Whitelist
                                  attributes=SAFE_ATTRS,
                                  strip=True))    # Remove everything else.


@register.filter
def strip_tags(s):
    return bleach.clean(s, strip=True)


@register.filter
def linkify(s, *args, **kwargs):
    return mark_safe(bleach.linkify(s, *args, **kwargs))


URN_PATTERNS = {
    'DOI': u'http://doi.org/{0}',
    'ISBN': u'http://www.worldcat.org/search?q=bn%3A{0}',
    'ISSN': u'http://www.worldcat.org/search?q=n2%3A{0}',
}


@register.filter
def linkeddata_for_display(ldinstance):
    value = ldinstance.universal_resource_name
    if ldinstance.type_controlled.name not in URN_PATTERNS:
        return value
    return URN_PATTERNS[ldinstance.type_controlled.name].format(value)

@register.filter
def get_doc_type_display(abbrev):
    for type in Citation.TYPE_CHOICES:
        if type[0].lower() == abbrev.lower():
            return type[1]

    return abbrev

@register.filter
def get_authority_type_display(abbrev):
    for type in Authority.TYPE_CHOICES:
        if type[0].lower() == abbrev.lower():
            return type[1]

    return abbrev
