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
    extra = []
    for obj in queryset:
        writer.writerow(map(lambda c: c(obj, extra), columns))
    print extra
    for obj in extra:
        print obj
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

    def __call__(self, obj, extra):
        try:
            if self.model is not None:
                assert isinstance(obj, self.model)
            return self.call(obj, extra)
        except AssertionError as E:    # Let this percolate through.
            raise E
        except Exception as E:
            print 'Exception in column %s for object %s' % (self.label, getattr(obj, 'id', None))
            print E
            return u""


def _citation_title(obj, extra):
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


def _citation_author(obj, extra):
    """
    Get the names of all authors on a citation.
    """
    names = obj.acrelation_set.filter(type_controlled=ACRelation.AUTHOR)\
                                   .order_by('data_display_order')\
                                   .values_list('name_for_display_in_citation',
                                                'authority__name')
    return u'; '.join(map(lambda o: o[0] if o[0] else o[1], filter(lambda o: o[0] or o[1], names)))


def _citation_editor(obj, extra):
    """
    Get the names of all editors on a citation.
    """
    names = obj.acrelation_set.filter(type_controlled=ACRelation.EDITOR)\
                                   .order_by('data_display_order')\
                                   .values_list('name_for_display_in_citation',
                                                'authority__name')
    return u'; '.join(map(lambda o: o[0] if o[0] else o[1], filter(lambda o: o[0] or o[1], names)))


def _subjects(obj, extra):
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
    return u'//'.join(filter(lambda o: o is not None,
                             list(qs.values_list('authority__name', flat=True))))


def _advisor(obj, extra):
    """
    ISISCB-936: "Adviser for thesis needs to be exported as a separate field".
    """
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & (Q(type_controlled=ACRelation.ADVISOR))
    qs = obj.acrelation_set.filter(_q)
    return u'//'.join(filter(lambda o: o is not None,
                             list(qs.values_list('authority__name', flat=True))))



def _category_numbers(obj, extra):
    """
    "Classification code" for the linked Classification Term
    """
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(authority__type_controlled=Authority.CLASSIFICATION_TERM)
    qs = obj.acrelation_set.filter(_q)
    return u'//'.join(filter(lambda o: o is not None, list(qs.values_list('authority__classification_code', flat=True))))


def _language(obj, extra):
    return u'//'.join(filter(lambda o: o is not None, list(obj.language.all().values_list('name', flat=True))))


def _place_publisher(obj, extra):
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(type_controlled=ACRelation.PUBLISHER)
    qs = obj.acrelation_set.filter(_q)
    if qs.count() == 0:
        return u''
    _first_publisher = qs.first()
    if _first_publisher.authority:
        return _first_publisher.authority.name
    return u''


def _school(obj, extra):
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(type_controlled=ACRelation.SCHOOL)
    qs = obj.acrelation_set.filter(_q)
    if qs.count() == 0:
        return u''
    _first_school = qs.first()
    if _first_school.authority:
        return _first_school.authority.name
    return u''


def _series(obj, extra):
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


def _isbn(obj, extra):
    """
    Get ISBN from LinkedData.
    """
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(type_controlled__name__iexact='isbn')
    qs = obj.linkeddata_entries.filter(_q)
    if qs.count() == 0:
        return u''
    return qs.first().universal_resource_name


def _pages(obj, extra):
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


def _tracking(obj, type_controlled):
    qs = obj.tracking_entries.filter(type_controlled=type_controlled)
    if qs.count() > 0:
        return u'//'.join(filter(lambda o: o is not None, list(qs.values_list('tracking_info', flat=True))))
    return u""


def _link_to_record(obj, extra):
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
    return u"//".join(filter(lambda o: o is not None, ids))


def _journal_link(obj, extra):
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(type_controlled=ACRelation.PERIODICAL)
    qs = obj.acrelation_set.filter(_q)
    if qs.count() == 0:
        return u""
    _first = qs.first()
    if _first.authority:
        return _first.authority.name
    return u""


def _journal_volume(obj, extra):
    if not hasattr(obj, 'part_details') or obj.part_details is None:
        return u""
    if obj.part_details.volume and len(obj.part_details.volume) > 0:
        return obj.part_details.volume
    return obj.part_details.volume_free_text


def _journal_issue(obj, extra):
    if not hasattr(obj, 'part_details') or obj.part_details is None:
        return u""

    if obj.part_details.issue_begin:
        iss = str(obj.part_details.issue_begin)
        if obj.part_details.issue_end:
            iss += u" - " + str(obj.part_details.issue_end)
        return iss
    return obj.part_details.issue_free_text


object_id = Column(u'Record ID', lambda obj, extra: obj.id)
citation_title = Column(u'Title', _citation_title, Citation)
citation_author = Column(u'Author', _citation_author, Citation)
record_type = Column('Record Type', lambda obj, extra: obj.get_type_controlled_display())
citation_editor = Column(u'Editor', _citation_editor, Citation)
year_of_publication = Column(u'Year of publication',
                             lambda obj, extra: obj.publication_date.year)
edition_details = Column(u'Edition Details', lambda obj, extra: obj.edition_details)
description = Column(u'Description', lambda obj, extra: obj.description)
subjects = Column(u'Subjects', _subjects)
category_numbers = Column(u'CategoryNumbers', _category_numbers)
language = Column(u'Language', _language)
place_publisher = Column(u'Place Publisher', _place_publisher)
physical_details = Column(u'Physical Details', lambda obj, extra: obj.physical_details)
series = Column(u'Series', _series)
isbn = Column(u'ISBN', _isbn)
pages = Column('Pages', _pages)
record_action = Column(u'Record Action',
                       lambda obj, extra: obj.get_record_action_display())
record_nature = Column(u'Record Nature',
                       lambda obj, extra: obj.get_record_status_value_display())
fully_entered = Column(u"FullyEntered",
                       lambda obj, extra: _tracking(obj, Tracking.FULLY_ENTERED))
proofed = Column(u"Proofed", lambda obj, extra: _tracking(obj, Tracking.PROOFED))
spw_checked = Column(u"SPW checked",
                     lambda obj, extra: _tracking(obj, Tracking.AUTHORIZED))
published_print = Column(u"Published Print",
                         lambda obj, extra: _tracking(obj, Tracking.PRINTED))
published_rlg = Column(u"Published RLG",
                       lambda obj, extra: _tracking(obj, Tracking.HSTM_UPLOAD))
link_to_record = Column(u"Link to Record", _link_to_record)
journal_link = Column(u"Journal Link", _journal_link)
journal_volume = Column(u"Journal Volume", _journal_volume)
journal_issue = Column(u"Journal Issue", _journal_issue)
advisor = Column("Advisor", _advisor)
school = Column(u"School", _school)


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
    advisor,
    school,
]
