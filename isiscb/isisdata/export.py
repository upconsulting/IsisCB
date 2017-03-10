"""
Module for bulk-exporting IsisCB data.

The strategy here is to favor extensibility/flexibility in defining output
columns, at the expense of performance. The performance hit is probably OK,
since these jobs will be performed asynchronously.
"""

from isisdata.models import *
from django.utils.text import slugify


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
    for obj in queryset:
        writer.writerow(map(lambda c: c(obj), columns))


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

    def __call__(self, obj):
        if self.model is not None:
            assert isinstance(obj, self.model)
        return self.call(obj)


def _citation_title(obj):
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


def _citation_author(obj):
    """
    Get the names of all authors on a citation.
    """
    names = obj.acrelation_set.filter(type_controlled=ACRelation.AUTHOR)\
                                   .order_by('data_display_order')\
                                   .values_list('name_for_display_in_citation',
                                                'authority__name')
    return u'; '.join(map(lambda o: o[0] if o[0] else o[1], filter(lambda o: o[0] or o[1], names)))


def _citation_editor(obj):
    """
    Get the names of all editors on a citation.
    """
    names = obj.acrelation_set.filter(type_controlled=ACRelation.EDITOR)\
                                   .order_by('data_display_order')\
                                   .values_list('name_for_display_in_citation',
                                                'authority__name')
    return u'; '.join(map(lambda o: o[0] if o[0] else o[1], filter(lambda o: o[0] or o[1], names)))


def _subjects(obj):
    """
    related authorites that are one of the following: subject, time, place,
    institution. Seperated by  double slashes //
    """
    _authority_types = [
        Authority.TIME_PERIOD, Authority.GEOGRAPHIC_TERM, Authority.INSTITUTION
    ]
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & (Q(authority__type_controlled__in=_authority_types) \
            | Q(type_controlled=ACRelation.SUBJECT))
    qs = obj.acrelation_set.filter(_q)
    return u'//'.join(list(qs.values_list('authority__name', flat=True)))


def _category_numbers(obj):
    """
    "Classification code" for the linked Classification Term
    """
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(authority__type_controlled=Authority.CLASSIFICATION_TERM)
    qs = obj.acrelation_set.filter(_q)
    return u'//'.join(list(qs.values_list('authority__classification_code', flat=True)))


def _language(obj):
    return u'//'.join(list(obj.language.all().values_list('name', flat=True)))


def _place_publisher(obj):
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(type_controlled=ACRelation.PUBLISHER)
    qs = obj.acrelation_set.filter(_q)
    return u'' if qs.count() == 0 else qs.first().authority.name


def _series(obj):
    """
    Book Series
    """
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(type_controlled=ACRelation.BOOK_SERIES)
    qs = obj.acrelation_set.filter(_q)
    return u'' if qs.count() == 0 else qs.first().authority.name


def _isbn(obj):
    """
    Get ISBN from LinkedData.
    """
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(type_controlled__name__iexact='isbn')
    qs = obj.linkeddata_entries.filter(_q)
    return u'' if qs.count() == 0 else qs.first().universal_resource_name


def _pages(obj):
    if obj.type_controlled != Citation.CHAPTER:
        return u""
    if not getattr(obj, 'part_details', None):
        return u""
    page_start_string = obj.part_details.page_begin
    page_end_string = obj.part_details.page_end
    if page_start_string and page_end_string:
        return u"pp. " + unicode(page_start_string) + "-" + unicode(page_end_string)
    if page_start_string:
        return u"p. " + unicode(page_start_string)
    if page_end_string:
        return u"p. " + unicode(page_end_string)
    return ""


def _tracking(obj, type_controlled):
    qs = obj.tracking_entries.filter(type_controlled=type_controlled)
    if qs.count() > 0:
        return u'//'.join(list(qs.values_list('tracking_info', flat=True)))
    return u""


def _link_to_record(obj):
    _ltypes = [Citation.CHAPTER, Citation.REVIEW, Citation.ESSAY_REVIEW]
    if obj.type_controlled not in _ltypes:
        return u""
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(type_controlled__in=[CCRelation.REVIEW_OF])
    ids = list(obj.ccrelations.filter(_q).values_list('object__id', flat=True))
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(type_controlled__in=[CCRelation.REVIEWED_BY,
                                  CCRelation.INCLUDES_CHAPTER])
    ids += list(obj.ccrelations.filter(_q).values_list('object__id', flat=True))
    return u"//".join(ids)


def _journal_link(obj):
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(type_controlled=ACRelation.PERIODICAL)
    qs = obj.acrelation_set.filter(_q)
    return u"" if qs.count() == 0 else qs.first().authority.id


def _journal_volume(obj):
    if not hasattr(obj, 'part_details') or obj.part_details is None:
        return u""
    if obj.part_details.volume and len(obj.part_details.volume) > 0:
        return obj.part_details.volume
    return obj.part_details.volume_free_text


def _journal_issue(obj):
    if not hasattr(obj, 'part_details') or obj.part_details is None:
        return u""

    if obj.part_details.issue_begin:
        iss = str(obj.part_details.issue_begin)
        if obj.part_details.issue_end:
            iss += u" - " + str(obj.part_details.issue_end)
        return iss
    return obj.part_details.issue_free_text


object_id = Column(u'Record ID', lambda obj: obj.id)
citation_title = Column(u'Title', _citation_title, Citation)
citation_author = Column(u'Author', _citation_author, Citation)
record_type = Column('Record Type', lambda obj: obj.get_type_controlled_display())
citation_editor = Column(u'Editor', _citation_editor, Citation)
year_of_publication = Column(u'Year of publication',
                             lambda obj: obj.publication_date.year)
edition_details = Column(u'Edition Details', lambda obj: obj.edition_details)
description = Column(u'Description', lambda obj: obj.description)
subjects = Column(u'Subjects', _subjects)
category_numbers = Column(u'CategoryNumbers', _category_numbers)
language = Column(u'Language', _language)
place_publisher = Column(u'Place Publisher', _place_publisher)
physical_details = Column(u'Physical Details', lambda obj: obj.physical_details)
series = Column(u'Series', _series)
isbn = Column(u'ISBN', _isbn)
pages = Column('Pages', _pages)
record_action = Column(u'Record Action',
                       lambda obj: obj.get_record_action_display())
record_nature = Column(u'Record Nature',
                       lambda obj: obj.get_record_status_value_display())
fully_entered = Column(u"FullyEntered",
                       lambda obj: _tracking(obj, Tracking.FULLY_ENTERED))
proofed = Column(u"Proofed", lambda obj: _tracking(obj, Tracking.PROOFED))
spw_checked = Column(u"SPW checked",
                     lambda obj: _tracking(obj, Tracking.AUTHORIZED))
published_print = Column(u"Published Print",
                         lambda obj: _tracking(obj, Tracking.PRINTED))
published_rlg = Column(u"Published RLG",
                       lambda obj: _tracking(obj, Tracking.HSTM_UPLOAD))
link_to_record = Column(u"Link to Record", _link_to_record)
journal_link = Column(u"Journal Link", _journal_link)
journal_volume = Column(u"Journal Volume", _journal_volume)
journal_issue = Column(u"Journal Issue", _journal_issue)


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
    pages,
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
]
