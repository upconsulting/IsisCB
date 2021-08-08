from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import str
from django import template
from isisdata.models import *

from django.conf import settings
from django.utils.safestring import mark_safe

from urllib.parse import quote
import codecs
import re
import urllib.parse

import bleach

register = template.Library()

@register.filter
def get_label_string(record):
    if type(record) == Citation:
        kwargs = {
            'authors': ", ".join([bleach_safe(contributor_as_string(x)) for x in get_authors(record)]),
            'title': bleach_safe(get_title(record)),
            'year': bleach_safe(get_pub_year(record)),
            }
        if record.type_controlled == Citation.BOOK:
            return u"{authors} <em>{title}</em> ({year})".format(**kwargs)
        return u'{authors} "{title}" ({year})'.format(**kwargs)

    if type(record) == Authority:
        return record.name

    return "None"

@register.filter(name='get_pk')
def get_pk(value):
    """
    Extracts Django primary key from SearchResult.id.
    """
    return value.split('.')[-1]


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
        if not citation.title_for_display:
            return "Title missing"
        return citation.title_for_display

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
def has_title(citation):
    # if citation is not a review simply return title
    if not citation.type_controlled == 'RE':
        if not citation.title:
            return False
        return True

    return True


@register.filter
def get_pub_year(citation):
    dates = citation.attributes.filter(type_controlled__name=settings.TIMELINE_PUBLICATION_DATE_ATTRIBUTE)
    if dates:
        if hasattr(dates[0].value.cvalue(), 'year'):
            year = dates[0].value.cvalue().year
        else:
            year = dates[0].value.cvalue()
        if type(year) == list and len(year) > 0:
            year = year[0]
        return dates[0].value_freeform if dates[0].value_freeform else year
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
def join_attributes_flat(attrlist, concator):
    return concator.join(attrlist)

@register.filter
def get_contributors(citation):
    return citation.acrelation_set.filter(type_controlled__in=['AU', 'CO', 'ED'], data_display_order__lt=30).order_by('data_display_order')


@register.filter
def contributor_as_string(acrelation):
    name = acrelation.name_for_display_in_citation
    if not name:
        name = acrelation.authority.name
    kwargs = {'name': name,
              'role': acrelation.get_type_controlled_display()}
    return u"{name}".format(**kwargs)


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
    if not s:
        return s
    return bleach.clean(s, tags={}, attributes={}, strip=True)


@register.filter
def linkify(s, *args, **kwargs):
    return mark_safe(bleach.linkify(s, *args, **kwargs))


@register.filter
def filter_abstract(s):
    """
    Some abstracts have metadata tags that should not be displayed in public
    views. If present, only the text between {AbstractBegin} and {AbstractEnd}
    should be displayed.
    """

    match = re.search('\{AbstractBegin\}([\w\s\W\S]*)\{AbstractEnd\}', s)
    if match:
        return match.groups()[0].strip()
    return s


@register.filter
def linkeddata_for_display(ldinstance):
    URN_PATTERNS = {
        'DOI': u'http://doi.org/{0}',
        'ISBN': u'http://www.worldcat.org/search?q=bn%3A{0}',
        'ISSN': u'http://www.worldcat.org/search?q=n2%3A{0}',
    }

    value = ldinstance.universal_resource_name.strip()
    if ldinstance.type_controlled.name not in URN_PATTERNS:
        return value

    # Make sure that the DOI is not already an URL.
    if urllib.parse.urlsplit(value).scheme:
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


@register.filter
def set_sort_order(link, sort_str):
    [key, sort_order] = sort_str.split(":")
    if not (key + "=") in link:
        return link + "&" + key + "=" + sort_order
    return re.sub(r"&" + key + "=[a-z_]+&?", "&" + key + "=" + sort_order + "&", link)


@register.filter
def set_sort_direction(link, sort_str):
    [key, sort_dir] = sort_str.split(":")
    if not (key + "=") in link:
        return link + "&" + key + "=" + sort_dir
    return re.sub(r"&"+ key +"=[a-z_]+&?", "&" + key + "=" + sort_dir + "&", link)


@register.filter
def set_page(link, sort_str):
    [key, page_number] = sort_str.split(":")
    if not (key + "=") in link:
        return link + "&" + key + "=" + str(page_number)
    return re.sub(r"&" + key + "=[0-9]+&?", "&" + key + "=" + str(page_number) + "&", link)


@register.filter
def set_index_model(link, model_str):
    [key, model] = model_str.split(':')
    if not (key + "=") in link:
        return link + "&" + key + "=" + model
    return re.sub(r"&" + key + "=isisdata\.[a-z]+&?", "&" + key + "=" + model + "&", link)


@register.filter
def get_current_sort_order_citation(sort_field):
    if not sort_field:
        return "Publication Date"
    if 'title_for_sort' in sort_field:
        return "Title"
    if 'author_for_sort' in sort_field:
        return "First Author"
    if 'publication_date_for_sort' in sort_field:
        return "Publication Date"
    if '_score' in sort_field:
        return 'Relevance'
    return sort_field


@register.filter
def get_user_id(user):
    """
    JavaScript-friendly user-id.
    """
    if user.id:
        return user.id
    return 'null'
