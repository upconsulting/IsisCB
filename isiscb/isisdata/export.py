"""
Module for bulk-exporting IsisCB data.

The strategy here is to favor extensibility/flexibility in defining output
columns, at the expense of performance. The performance hit is probably OK,
since these jobs will be performed asynchronously.
"""

from isisdata.models import *
from django.utils.text import slugify
import functools


def generate_csv(stream, queryset, columns):
    """
    Write data from a queryset as CSV to a file/stream.

    Note: this is for synchronous export only. An asynchronous implementation
    can be found in :mod:`isisdata.tasks`\.

    Parameters
    ----------
    stream : object
        A file pointer, or anything that provides a ``write()`` method.
    queryset : iterable
        Each object yielded will be passed to the column handlers in
        ``columns``.
    columns : list
        Should be a list of :class:`.Column` instances.
    """

    import unicodecsv as csv
    writer = csv.writer(stream)
    writer.writerow(map(lambda c: c.label, columns))
    extra = []
    for obj in queryset:
        if obj is not None:
            writer.writerow(map(lambda c: c(obj, extra), columns))

    for obj in extra:
        if obj is not None:
            writer.writerow(map(lambda c: c(obj, []), columns))


class Column(object):
    """
    Convenience wrapper for functions that generate column data.

    Parameters
    ----------
    label : str
        Label used as the column header in the output document.
    fnx : callable
        Should take a single object (e.g. a model instance), and return unicode.
    model : class
        Optional. If provided, an AssertionError will be raised if the column
        is passed an object that is not an instance of ``model``.
    """
    def __init__(self, label, fnx, model=None):
        assert hasattr(fnx, '__call__')
        self.label = label
        self.call = fnx
        self.model = model
        self.slug = slugify(label)

    def __call__(self, obj, extra, config={}):
        try:
            if self.model is not None:
                assert isinstance(obj, self.model)
            return self.call(obj, extra, config)
        except AssertionError as E:    # Let this percolate through.
            raise E
        except Exception as E:
            print 'Exception in column %s for object %s' % (self.label, getattr(obj, 'id', None))
            print E
            return u""


def _citation_title(obj, extra, config={}):
    """
    Get the production title for a citation.
    """
    # if citation is not a review simply return title
    if not obj.type_controlled == Citation.REVIEW:
        if not obj.title:
            return u"Title missing"
        return obj.title

    # if citation is a review build title from reviewed citation
    reviewed_books = obj.relations_from.filter(type_controlled=CCRelation.REVIEW_OF)

    # sometimes RO relationship is not specified then use inverse reviewed by
    book = None
    if not reviewed_books:
        reviewed_books = obj.relations_to.filter(type_controlled=CCRelation.REVIEWED_BY)
        if reviewed_books:
            book = reviewed_books.first().subject
    else:
        book = reviewed_books.first().object

    if book is None:
        return u"Review of unknown publication"
    return u'Review of "%s"' % book.title

# adjustment of export according to ISISCB-1033
def create_acr_string(author, additional_fields = [], delimiter=u" "):
    fields = ['ACR_ID ' + str(author[0]),
               'ACRStatus ' + (str(author[1]) if author[1] else u''),
               'ACRType ' + (dict(ACRelation.TYPE_CHOICES)[author[2]] if author[2] else u''),
               'ACRDisplayOrder ' + (str(author[3]) if author[3] else u''),
               'ACRNameForDisplayInCitation ' + (author[4] if author[4] else u''),
               'AuthorityID ' + (str(author[5]) if author[5] else u''),
               'AuthorityStatus ' + (str(author[6]) if author[6] else u''),
               'AuthorityType ' + (dict(Authority.TYPE_CHOICES)[author[7]] if author[7] else u''),
               'AuthorityName ' + (author[8] if author[8] else u'')
                ]
    return delimiter.join(fields + [field_name + ' ' + str(author[9+idx]) for idx,field_name in enumerate(additional_fields)])
acr_fields = ['id',
          'record_status_value',
          'type_controlled',
          'data_display_order',
          'name_for_display_in_citation',
          'authority__id',
          'authority__record_status_value',
          'authority__type_controlled',
          'authority__name'
         ]

def create_ccr_string(ccr, additional_fields = [], delimiter=u" "):
    fields = ['CCR_ID ' + str(ccr[0]),
               'CCRStatus  ' + str(ccr[1]),
               'CCRType  ' + dict(CCRelation.TYPE_CHOICES)[ccr[2]],
               'CitationID  ' + str(ccr[3]),
               'CitationStatus  ' + str(ccr[4]),
               'CitationType  ' + dict(Citation.TYPE_CHOICES)[ccr[5]],
               'CitationTitle  ' + ccr[6]
                ]
    return delimiter.join(fields + [field_name + ' ' + str(author[9+idx]) for idx,field_name in enumerate(additional_fields)])

ccr_from_fields = ['id',
          'record_status_value',
          'type_controlled',
          'object__id',
          'object__record_status_value',
          'object__type_controlled',
          'object__title'
         ]
ccr_to_fields = ['id',
          'record_status_value',
          'type_controlled',
          'subject__id',
          'subject__record_status_value',
          'subject__type_controlled',
          'subject__title'
         ]

def _get_fields_delimiter(config):
    if 'authority_delimiter' in config:
        return config['authority_delimiter']
    else:
        return " "

def _citation_author(obj, extra, config={}):
    """
    Get the names of all authors on a citation.
    """
    names = obj.acrelation_set.filter(type_controlled=ACRelation.AUTHOR)\
                                   .order_by('data_display_order')\
                                   .values_list(*acr_fields)

    return u' // '.join(map(functools.partial(create_acr_string,delimiter=_get_fields_delimiter(config)), names))

def _citation_editor(obj, extra, config={}):
    """
    Get the names of all editors on a citation.
    """
    names = obj.acrelation_set.filter(type_controlled=ACRelation.EDITOR)\
                                   .order_by('data_display_order')\
                                   .values_list(*acr_fields)
    return u' // '.join(map(functools.partial(create_acr_string,delimiter=_get_fields_delimiter(config)), names))


def _subjects(obj, extra, config={}):
    """
    related authorites that are one of the following: subject, time, place,
    institution. Seperated by  double slashes //
    """
    _authority_types = [
        Authority.TIME_PERIOD, Authority.GEOGRAPHIC_TERM, Authority.INSTITUTION
    ]
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & (Q(authority__type_controlled__in=_authority_types) \
            | Q(type_controlled=ACRelation.SUBJECT)) \
         & ~Q(type_controlled=ACRelation.SCHOOL)
    qs = obj.acrelation_set.filter(_q)
    return u' // '.join(map(functools.partial(create_acr_string,delimiter=_get_fields_delimiter(config)), qs.values_list(*acr_fields)))


def _advisor(obj, extra, config={}):
    """
    ISISCB-936: "Adviser for thesis needs to be exported as a separate field".
    """
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & (Q(type_controlled=ACRelation.ADVISOR))
    qs = obj.acrelation_set.filter(_q)
    return u' // '.join(map(functools.partial(create_acr_string,delimiter=_get_fields_delimiter(config)), qs.values_list(*acr_fields)))


def _category_numbers(obj, extra, config={}):
    """
    "Classification code" for the linked Classification Term
    """
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(authority__type_controlled=Authority.CLASSIFICATION_TERM)
    qs = obj.acrelation_set.filter(_q)
    return u' // '.join(map(functools.partial(create_acr_string, additional_fields=['ClassificationCode'], delimiter=_get_fields_delimiter(config)), qs.values_list(*(acr_fields+['authority__classification_code']))))


def _language(obj, extra, config={}):
    return u'//'.join(filter(lambda o: o is not None, list(obj.language.all().values_list('name', flat=True))))


def _place_publisher(obj, extra, config={}):
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(type_controlled=ACRelation.PUBLISHER)
    qs = obj.acrelation_set.filter(_q)
    return u' // '.join(map(functools.partial(create_acr_string,delimiter=_get_fields_delimiter(config)), qs.values_list(*acr_fields)))


def _school(obj, extra, config={}):
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(type_controlled=ACRelation.SCHOOL)
    qs = obj.acrelation_set.filter(_q)
    return u' // '.join(map(functools.partial(create_acr_string,delimiter=_get_fields_delimiter(config)), qs.values_list(*acr_fields)))


def _series(obj, extra, config={}):
    """
    Book Series
    """
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(type_controlled=ACRelation.BOOK_SERIES)
    qs = obj.acrelation_set.filter(_q)
    if qs.count() == 0:
        return u''
    _first_series = qs.first()
    if _first_series.authority:
        return _first_series.authority.name
    return u''


def _isbn(obj, extra, config={}):
    """
    Get ISBN from LinkedData.
    """
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(type_controlled__name__iexact='isbn')
    qs = obj.linkeddata_entries.filter(_q)
    if qs.count() == 0:
        return u''
    return qs.first().universal_resource_name

def _linked_data(obj, extra, config={}):
    """
    Get linked data entries
    """
    qs = obj.linkeddata_entries.all()
    if qs.count() == 0:
        return u''

    return u' // '.join(map(lambda x: u' '.join(['Type ' + (x[0] if x[0] else ''), 'URN ' + (x[1] if x[1] else '')]), qs.values_list(*['type_controlled__name', 'universal_resource_name'])))

def _pages(obj, extra, config={}):
    if not getattr(obj, 'part_details', None):
        return u""
    page_start_string = obj.part_details.page_begin
    page_end_string = obj.part_details.page_end
    if obj.type_controlled == Citation.CHAPTER:
        if page_start_string and page_end_string:
            pre = u"pp."
        else:
            pre = u"p."
    else:
        pre = u""
    if page_start_string and page_end_string:
        return pre + unicode(page_start_string) + "-" + unicode(page_end_string)
    if page_start_string:
        return pre + unicode(page_start_string)
    if page_end_string:
        return pre + unicode(page_end_string)
    return ""

def _pages_free_text(obj, extra, config={}):
    if not getattr(obj, 'part_details', None):
        return u""
    return obj.part_details.pages_free_text + " (From %s // To %s)" % (obj.part_details.page_begin if obj.part_details.page_begin else u'', obj.part_details.page_end if obj.part_details.page_end else u'')

def _tracking(obj, type_controlled):
    qs = obj.tracking_records.filter(type_controlled=type_controlled)
    if qs.count() > 0:
        # format: tracking id: date or tracking info
        # this is ugly but well:
        # if there is a creation date (modification date since we never change them again), use the date
        # otherwise use tracking info
        return u'//'.join(map(lambda o: "%s: %s"%(o[1], (o[2] if o[2] else (o[0] if o[0] else ""))), list(qs.values_list('tracking_info', 'id', 'modified_on'))))
    return u""


def _link_to_record(obj, extra, config={}):
    _ltypes = [Citation.CHAPTER, Citation.REVIEW, Citation.ESSAY_REVIEW]
    if obj.type_controlled not in _ltypes:
        return u""
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(type_controlled__in=[CCRelation.REVIEW_OF])
    qs = obj.ccrelations.filter(_q)
    extra += map(lambda o: o.object, qs)
    ids = list(qs.values_list('object__id', flat=True))
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(type_controlled__in=[CCRelation.REVIEWED_BY,
                                  CCRelation.INCLUDES_CHAPTER])
    qs = obj.ccrelations.filter(_q)
    extra += map(lambda o: o.subject, qs)
    ids += list(qs.values_list('subject__id', flat=True))
    return u" // ".join(filter(lambda o: o is not None, ids))


def _journal_link(obj, extra, config={}):
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(type_controlled=ACRelation.PERIODICAL)
    qs = obj.acrelation_set.filter(_q)
    if qs.count() == 0:
        return u""
    _first = qs.first()
    if _first.authority:
        return _first.authority.name
    return u""


def _journal_volume(obj, extra, config={}):
    if not hasattr(obj, 'part_details') or obj.part_details is None:
        return u""
    # ISISCB-1033
    return obj.part_details.volume_free_text + u" (From %s // To %s)" % (obj.part_details.volume_begin if obj.part_details.volume_begin else u'', obj.part_details.volume_end if obj.part_details.volume_end else u'')


def _journal_issue(obj, extra, config={}):
    if not hasattr(obj, 'part_details') or obj.part_details is None:
        return u""
    # ISISCB-1033
    return obj.part_details.issue_free_text + u" (From %s // To %s)" % (obj.part_details.issue_begin if obj.part_details.issue_begin else u'', obj.part_details.issue_end if obj.part_details.issue_end else u'')


def _includes_series_article(obj, extra, config={}):
    qs = obj.relations_to.filter(type_controlled=CCRelation.INCLUDES_SERIES_ARTICLE)
    extra += map(lambda o: o.subject, qs)
    return u" // ".join(filter(lambda o: o is not None, qs.values_list('subject_id', flat=True)))

def _related_authorities(obj, extra, config={}):
    qs = obj.acrelation_set.all()
    return u' // '.join(map(functools.partial(create_acr_string,delimiter=_get_fields_delimiter(config)), qs.values_list(*acr_fields)))

def _related_citations(obj, extra, config={}):
    qs_from = obj.relations_from.all()
    qs_to = obj.relations_to.all()

    return u' // '.join(map(functools.partial(create_ccr_string,delimiter=_get_fields_delimiter(config)), qs_from.values_list(*ccr_from_fields)) + map(functools.partial(create_ccr_string,delimiter=_get_fields_delimiter(config)), qs_to.values_list(*ccr_to_fields)))


def _extent(obj, extra, config={}):
    if not hasattr(obj, 'part_details') or obj.part_details is None:
        return u""
    return u"%s (Note %s)" % (obj.part_details.extent if obj.part_details.extent else u'', obj.part_details.extent_note if obj.part_details.extent_note else u'')

def _attributes(obj, extra, config={}):
    qs = obj.attributes.all()

    if qs.count() > 0:
        return u' // '.join(map(lambda x: u' '.join(['Type ' + x.type_controlled.name, 'Value ' + str(x.value.cvalue()), 'FreeFormValue ' + x.value_freeform]), qs))

    return u""

def _record_status(obj, extra, config={}):
    return u"%s (RecordStatusExplanation %s)"%(obj.get_record_status_value_display(), obj.record_status_explanation if obj.record_status_explanation else u'')

def _dataset(obj, extra, config={}):
    if not obj.belongs_to:
        return u""

    return obj.belongs_to.name

def _created_on(obj, extra, config={}):
    try:
        return obj.history.get(history_type='+').history_date
    except:
        return u""

object_id = Column(u'Record ID', lambda obj, extra, config={}: obj.id)
citation_title = Column(u'Title', _citation_title, Citation)
citation_author = Column(u'Author', _citation_author, Citation)
record_type = Column('Record Type', lambda obj, extra, config={}: obj.get_type_controlled_display())
citation_editor = Column(u'Editor', _citation_editor, Citation)
year_of_publication = Column(u'Year of publication',
                             lambda obj, extra, config={}: obj.publication_date.year)
edition_details = Column(u'Edition Details', lambda obj, extra, config={}: obj.edition_details)
description = Column(u'Description', lambda obj, extra, config={}: obj.description)
subjects = Column(u'Subjects', _subjects)
category_numbers = Column(u'CategoryNumbers', _category_numbers)
language = Column(u'Language', _language)
place_publisher = Column(u'Place Publisher', _place_publisher)
physical_details = Column(u'Physical Details', lambda obj, extra, config={}: obj.physical_details)
series = Column(u'Series', _series)
isbn = Column(u'ISBN', _isbn)
pages = Column('Pages', _pages)
pages_free_text = Column('Pages Free Text', _pages_free_text)
record_action = Column(u'Record Action',
                       lambda obj, extra, config={}: obj.get_record_action_display())
record_nature = Column(u'Record Nature', _record_status)
fully_entered = Column(u"FullyEntered",
                       lambda obj, extra, config={}: _tracking(obj, Tracking.FULLY_ENTERED))
proofed = Column(u"Proofed", lambda obj, extra, config={}: _tracking(obj, Tracking.PROOFED))
spw_checked = Column(u"SPW checked",
                     lambda obj, extra, config={}: _tracking(obj, Tracking.AUTHORIZED))
published_print = Column(u"Published Print",
                         lambda obj, extra, config={}: _tracking(obj, Tracking.PRINTED))
published_rlg = Column(u"Published RLG",
                       lambda obj, extra, config={}: _tracking(obj, Tracking.HSTM_UPLOAD))
link_to_record = Column(u"Link to Record", _link_to_record)
journal_link = Column(u"Journal Link", _journal_link)
journal_volume = Column(u"Journal Volume", _journal_volume)
journal_issue = Column(u"Journal Issue", _journal_issue)
advisor = Column("Advisor", _advisor)
school = Column(u"School", _school)
include_series_article = Column(u"Includes Series Article",
                                _includes_series_article)
extent = Column(u"Extent", _extent)
linked_data = Column(u"Linked Data", _linked_data)
attributes = Column(u"Attributes", _attributes)
related_authorities = Column(u"Related Authorities", _related_authorities)
related_citations = Column(u"Related Citations", _related_citations)
abstract = Column(u"Abstract", lambda obj, extra, config={}: obj.abstract)
staff_notes = Column(u"Staff Notes", lambda obj, extra, config={}: obj.administrator_notes)
record_history = Column(u"Record History", lambda obj, extra, config={}: obj.record_history)
dataset = Column(u"Dataset", _dataset)
created_on = Column(u"Created Date", _created_on)
modified_on = Column(u"Modified Date", lambda obj, extra, config={}: obj._history_date)

CITATION_COLUMNS = [
    object_id,
    citation_title,
    citation_author,
    record_type,
    citation_editor,
    year_of_publication,
    edition_details,
    description,
    subjects,
    category_numbers,
    language,
    place_publisher,
    physical_details,
    series,
    isbn,
    #pages,
    pages_free_text,
    record_action,
    record_nature,
    fully_entered,
    proofed,
    spw_checked,
    published_print,
    published_rlg,
    link_to_record,
    journal_link,
    journal_volume,
    journal_issue,
    advisor,
    school,
    include_series_article,
    extent,
    linked_data,
    attributes,
    related_authorities,
    related_citations,
    abstract,
    staff_notes,
    record_history,
    dataset,
    created_on,
    modified_on
]
