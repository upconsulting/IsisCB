from __future__ import unicode_literals
from builtins import str
from past.builtins import basestring
from django import template
from django.utils.safestring import SafeText
from django.db.models import Q
from django.db.utils import ProgrammingError

from isisdata.models import *
import logging

register = template.Library()

logger = logging.getLogger(__name__)

try:
    PUBLICATION_DATE = AttributeType.objects.get(name='PublicationDate').id
except AttributeType.DoesNotExist:
    PUBLICATION_DATE = -1
except ProgrammingError as e:
    print("Could not get publication dates.", e)

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
        rtypes = [CCRelation.REVIEW_OF, CCRelation.REVIEWED_BY]
        relation = obj.ccrelations.select_related('subject', 'object')\
            .filter(type_controlled__in=rtypes)\
            .values('subject_id', 'subject__title', 'object__title')
        if relation.count() > 0:
            relation = relation.first()
        else:
            relation = None
        if relation:
            if relation['subject__title'] or relation['object__title']:
                return u'Review: %s' % relation['subject__title'] if relation['subject_id'] != obj.id else relation['object__title']
            else:
                return u'(no title)'
        return u'Untitled review'
    return title


@register.filter(name='get_publisher')
def get_publisher(obj):
    return obj.acrelations.filter(type_controlled=ACRelation.PUBLISHER).first()

@register.filter(name='get_isbn')
def get_isbn(obj):
    return obj.linkeddata_entries.filter(type_controlled__name__icontains='isbn').first()


@register.filter(name='get_doi')
def get_doi(obj):
    return obj.linkeddata_entries.filter(type_controlled__name__icontains='doi').first()


@register.filter(name='get_authors_editors')
def get_authors_editors(obj):
    author_names = []
    for relation in obj.acrelations:
        if relation.type_controlled in [ACRelation.AUTHOR, ACRelation.EDITOR]:
            name = getattr(relation.authority, 'name', None)
            if not name:
                name = getattr(relation, 'name_for_display_in_citation') or "missing"
            name = name + ' ('+  relation.get_type_controlled_display() + ') '
            author_names.append(name)

    return ', '.join(author_names)

@register.filter
def get_authors_editors_relations(obj):
    return [relation for relation in obj.acrelations if relation.type_controlled in [ACRelation.AUTHOR, ACRelation.EDITOR]]

@register.filter(name='get_authors_editors_no_type')
def get_authors_editors_no_type(obj):
    return ', '.join([getattr(relation.authority, 'name', 'missing') for relation in obj.acrelations
                if relation.type_controlled in [ACRelation.AUTHOR, ACRelation.EDITOR]])


@register.filter(name='get_authors_advisors')
def get_authors_advisors(obj):
    return ', '.join([getattr(relation.authority, 'name', 'missing') + ' ('+  relation.get_type_controlled_display() + ')' for relation in obj.acrelations
                if relation.type_controlled in [ACRelation.AUTHOR, ACRelation.ADVISOR]])

@register.filter
def get_authors_advisors_relations(obj):
    return [relation for relation in obj.acrelations if relation.type_controlled in [ACRelation.AUTHOR, ACRelation.ADVISOR]]


@register.filter(name='get_authors_editors_preloaded')
def get_authors_editors_preloaded(citation_id):
    rtypes = [ACRelation.AUTHOR, ACRelation.EDITOR]
    qs = ACRelation.objects.filter(citation_id=citation_id, type_controlled__in=rtypes).values('authority__name', 'type_controlled', 'name_for_display_in_citation')
    rtype_display = dict(ACRelation.TYPE_CHOICES)
    return ', '.join(['%s (%s)' % (obj.get('authority__name', None) or (obj.get('name_for_display_in_citation') + " [no link]" if obj.get('name_for_display_in_citation') else None) or 'missing', rtype_display[obj['type_controlled']]) for obj in qs])

@register.filter(name='get_citation_pubdate')
def get_citation_pubdate(obj):
    for attribute in obj.attributes.all():
        if attribute.type_controlled.name == 'PublicationDate':
            try:
                return attribute.value.get_child_class().__unicode__()
            except Exception as e:
                logger.error("Could not get publication date.")
                logger.error(e)
                return ""

    date = getattr(obj, 'publication_date', None)
    return 'missing' if not date else date.isoformat()[:4]

@register.filter(name='get_citation_moddate')
def get_citation_moddate(obj):
    for attribute in obj.attributes.all():
        if attribute.type_controlled.name == 'ModifiedDate':
            return attribute.value.get_child_class().__unicode__()

    return 'missing'

@register.filter(name='get_citation_accdate')
def get_citation_moddate(obj):
    for attribute in obj.attributes.all():
        if attribute.type_controlled.name == 'LastAccessedDate':
            return attribute.value.get_child_class().__unicode__()

    return 'missing'

@register.filter(name='get_citation_website_title')
def get_citation_website_title(obj):
    for attribute in obj.attributes.all():
        if attribute.type_controlled.name == 'WebsiteTitle':
            return attribute.value.get_child_class().__unicode__()

    return 'missing'

@register.filter(name='get_citation_website_subtype')
def get_citation_website_subtype(obj):
    for attribute in obj.attributes.all():
        if attribute.type_controlled.name == 'TypeOfWebsite':
            return attribute.value.get_child_class().__unicode__()

    return 'missing'


@register.filter(name='get_citation_pubdate_fast')
def get_citation_pubdate_fast(obj):
    date = getattr(obj, 'publication_date', None)
    if not date:
        return 'missing'
    return date.isoformat()[:4]


@register.filter
def get_reviewed_books(citation):
    ccrelations = citation.ccrelations.filter(Q(type_controlled=CCRelation.REVIEW_OF, subject__id=citation.id))
    citations =  [x.object for x in ccrelations]

    ccrelations = citation.ccrelations.filter(Q(type_controlled=CCRelation.REVIEWED_BY, object__id=citation.id))
    citations = citations + [x.subject for x in ccrelations]

    return citations


@register.filter
def get_including_book(citation):
    ccrelations = citation.ccrelations.filter(Q(type_controlled=CCRelation.INCLUDES_CHAPTER, object__id=citation.id))
    citations =  [x.subject for x in ccrelations]

    return citations


@register.filter
def get_pub_title_and_year(citation):
    return u"{0}, ({1})".format(citation.title, getattr(citation, 'publication_date', "Date missing"))


@register.filter(name='get_citation_periodical')
def get_citation_periodical(citation_id):
    rtypes = [ACRelation.PUBLISHER, ACRelation.PERIODICAL, ACRelation.BOOK_SERIES]
    atype_display = dict(Authority.TYPE_CHOICES)
    relations = ACRelation.objects.filter(citation_id=citation_id, type_controlled__in=rtypes).values('authority__name', 'authority__type_controlled', 'name_for_display_in_citation')
    return ', '.join(['%s (%s)' % (obj.get('authority__name') or (obj.get('name_for_display_in_citation') + " [no link]" if obj.get('name_for_display_in_citation') else None) or "missing", atype_display.get(obj['authority__type_controlled'], 'none')) for obj in relations])

@register.filter
def get_citation_periodical_relations(citation_id):
    rtypes = [ACRelation.PUBLISHER, ACRelation.PERIODICAL, ACRelation.BOOK_SERIES]
    return ACRelation.objects.filter(citation_id=citation_id, type_controlled__in=rtypes)

@register.filter(name='get_page_numbers')
def get_page_numbers(obj):
    if 'part_details_id' not in obj:
        return u''
    if not obj.get('part_details__page_end') and obj.get('part_details__pages_free_text'):
        return obj.get('part_details__pages_free_text')
    return ' - '.join([str(p) for p in [obj.get('part_details__page_begin'), obj.get('part_details__page_end')] if p])

@register.filter
def get_school(obj):
    return ', '.join(['%s (%s)' % (getattr(relation.authority, 'name', ''), relation.get_type_controlled_display()) for relation in obj.acrelations
        if relation.authority is not None and relation.type_controlled in [ACRelation.SCHOOL]])


@register.filter(name='get_date_attributes')
def get_date_attributes(obj):
    try:
        return SafeText(', '.join(['<span class="label label-success">%s</span> %s' % (attribute.type_controlled.name, attribute.value.display) for attribute in obj.attributes.all()]))
    except:
        return ''

@register.filter
def is_ccrelation_other_public(instance_id, ccrelation):
    return (ccrelation.subject is not None and ccrelation.object is not None) and (instance_id == ccrelation.subject.id and not getattr(ccrelation.object, 'public', False)) or (instance_id == ccrelation.object.id and not getattr(ccrelation.subject, 'public', False))


@register.filter
def get_categories(obj):
    return ACRelation.objects.filter(type_controlled=ACRelation.CATEGORY, citation_id=obj.id)


@register.filter
def get_other_subjects(obj):
    return ACRelation.objects.\
        filter(type_controlled=ACRelation.SUBJECT, citation_id=obj.id).\
        exclude(authority__type_controlled__in=[
            Authority.TIME_PERIOD, Authority.GEOGRAPHIC_TERM, Authority.PERSON, Authority.INSTITUTION
        ])

@register.filter
def get_time_and_place_subjects(obj):
    return ACRelation.objects.filter(type_controlled=ACRelation.SUBJECT, authority__type_controlled__in=[Authority.TIME_PERIOD, Authority.GEOGRAPHIC_TERM], citation_id=obj.id)

@register.filter
def get_person_subjects(obj):
    return ACRelation.objects.filter(type_controlled=ACRelation.SUBJECT, authority__type_controlled__in=[Authority.PERSON], citation_id=obj.id)

@register.filter
def get_person_and_institutions_subjects(obj):
    return ACRelation.objects.filter(type_controlled=ACRelation.SUBJECT, authority__type_controlled__in=[Authority.PERSON, Authority.INSTITUTION], citation_id=obj.id)

TRACKING_STATES = dict(Citation.TRACKING_CHOICES)
CITATION_TYPES = dict(Citation.TYPE_CHOICES)
AUTHORITY_TRACKING_STATES = dict(Authority.TRACKING_CHOICES)
AUTHORITY_TYPES = dict(Authority.TYPE_CHOICES)


@register.filter
def get_tracking_state_display(state):
    return TRACKING_STATES.get(state) if TRACKING_STATES.get(state) else state


@register.filter
def get_authority_tracking_state_display(state):
    return AUTHORITY_TRACKING_STATES.get(state)


@register.filter
def get_type_controlled_display(type_controlled):
    return CITATION_TYPES.get(type_controlled)


@register.filter
def get_authority_type_controlled_display(type_controlled):
    return AUTHORITY_TYPES.get(type_controlled)

@register.filter
def get_status_label(status):
    # get_record_status_type_display doesn't work in template because we don't have the object
    status_dict = dict(CuratedMixin.STATUS_CHOICES)
    return status_dict[status]

@register.filter
def get_iso_date(date):
    return '' if not date else date.isoformat()

@register.filter
def cut_characters(string, cut):
    if string and len(string) > cut:
        return string[:cut]
    return string

@register.filter
def order_by(queryset, args):
    args = [x.strip() for x in args.split(',')]
    return queryset.order_by(*args)

@register.filter
def get_other_relation_side(ccrel, elem):
    if ccrel.subject.id == elem.id:
        return ccrel.object
    return ccrel.subject

@register.filter('startswith')
def startswith(text, starts):
    if isinstance(text, basestring):
        return text.startswith(starts)
    return False

@register.filter
def get_label_class(authority):
    label_classes = {
        Authority.TIME_PERIOD: "chronology",
        Authority.GEOGRAPHIC_TERM: "geography",
        Authority.PERSON: "person",
        Authority.INSTITUTION: "institution",
        Authority.CONCEPT: "concept",
    }

    return label_classes.get(authority.type_controlled, "other")
