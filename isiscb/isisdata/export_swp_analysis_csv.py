"""
Module for bulk-exporting IsisCB data in EBSCO format.

The strategy here is to favor extensibility/flexibility in defining output
columns, at the expense of performance. The performance hit is probably OK,
since these jobs will be performed asynchronously.
"""

from isisdata.models import *
from django.utils.text import slugify
import functools
import export_item_count_csv
from django.conf import settings


def _authors_editors_names(obj, extra, config={}):
    fields = ['authority__id', 'authority__name', 'type_controlled']
    names = obj.acrelation_set.filter(type_controlled__in=[ACRelation.EDITOR, ACRelation.AUTHOR])\
                                   .order_by('data_display_order')\
                                   .values_list(*fields)
    return u' // '.join(map(lambda x: "AuthorityID %s || AuthorityName %s || Role %s"%(x[0], x[1], dict(ACRelation.TYPE_CHOICES)[x[2]]), names))

def _publisher_school(obj, extra, config={}):
    if obj.type_controlled in [Citation.BOOK, Citation.CHAPTER]:
        obj_with_publisher = obj
        # if we have a chapter we need to get the connect book
        if obj.type_controlled == Citation.CHAPTER:
            book_ccr = obj.ccrelations.filter(type_controlled__in=[CCRelation.INCLUDES_CHAPTER])
            if book_ccr and book_ccr.first():
                obj = book_ccr.first().subject

        # get publisher
        fields = ['authority__id', 'authority__name']
        names = obj.acrelation_set.filter(type_controlled=ACRelation.PUBLISHER)\
                                       .values_list(*fields)

        return u' // '.join(map(lambda x: "AuthorityID %s || AuthorityName %s"%(x[0], x[1]), names))

    # school missing

def _journal_name(obj, extra, config={}):
    qs = obj.acrelation_set.filter(type_controlled=ACRelation.PERIODICAL)
    if qs.count() == 0:
        return u""
    _first = qs.first()
    if _first.authority:
        return unicode(_first.authority.name)
    return u""

def _volume(obj, extra, config={}):
    if not hasattr(obj, 'part_details') or obj.part_details is None:
        return u""
    # ISISCB-1033
    if obj.part_details.volume_free_text and obj.part_details.volume_free_text.strip():
        return obj.part_details.volume_free_text.strip()

    if obj.part_details.volume_begin or obj.part_details.volume_end:
        return "-".join(map(lambda x: str(x), filter(None, [obj.part_details.volume_begin, obj.part_details.volume_end])))

    return ''

def _pages_free_text(obj, extra, config={}):
    if not getattr(obj, 'part_details', None):
        return u""
    if obj.part_details.pages_free_text and obj.part_details.pages_free_text.strip():
        return obj.part_details.pages_free_text.strip()

    if obj.part_details.page_begin or obj.part_details.page_end:
        return "-".join(map(lambda x: str(x), filter(None, [obj.part_details.page_begin, obj.part_details.page_end])))

    return ''

def _category(obj, extra, config={}):
    fields = ['authority__name']
    names = obj.acrelation_set.filter(type_controlled=ACRelation.CATEGORY)\
                                   .values_list(*fields)
    return u' || '.join(map(lambda x: x[0], names))

def _language(obj, extra, config={}):
    return u' || '.join(filter(lambda o: o is not None, list(obj.language.all().values_list('name', flat=True))))


object_id = export_item_count_csv.Column(u'Record number', lambda obj, extra, config={}: obj.id)
print_status = export_item_count_csv.Column(u'Print status', export_item_count_csv._print_status)
record_status = export_item_count_csv.Column(u'Record Status', lambda obj, extra, config={}: obj.get_record_status_value_display())
citation_title = export_item_count_csv.Column(u'Title', export_item_count_csv._citation_title, Citation)
record_type = export_item_count_csv.Column('Record Type', export_item_count_csv._record_type)
authors_editors_names = export_item_count_csv.Column('Author/Editor Names', _authors_editors_names)
publisher_school = export_item_count_csv.Column('Publisher/School', _publisher_school)
journal_name = export_item_count_csv.Column("Journal Name", _journal_name)
year_of_publication = export_item_count_csv.Column(u'Year Published', lambda obj, extra, config={}: obj.publication_date.year)
volume = export_item_count_csv.Column(u"Volume", _volume)
pages_free_text = export_item_count_csv.Column(u"Pages", _pages_free_text)
category = export_item_count_csv.Column(u"Category", _category)
language = export_item_count_csv.Column(u"Language", _language)
tracking_records = export_item_count_csv.Column('Tracking Records', export_item_count_csv._tracking_records)
record_action = export_item_count_csv.Column(u'Record Action', lambda obj, extra, config={}: obj.get_record_action_display())
related_citations = export_item_count_csv.Column('Related Citations', export_item_count_csv._related_citations)
staff_notes = export_item_count_csv.Column(u"Staff Notes", lambda obj, extra, config={}: obj.administrator_notes)
record_history = export_item_count_csv.Column(u"Record History", lambda obj, extra, config={}: obj.record_history)
dataset = export_item_count_csv.Column(u"Dataset", export_item_count_csv._dataset)
created_date = export_item_count_csv.Column(u"Created Date", export_item_count_csv._created_date)
modified_date = export_item_count_csv.Column(u"Modified Date",export_item_count_csv. _modified_date)


CITATION_COLUMNS = [
    object_id,
    print_status,
    record_status,
    citation_title,
    record_type,
    authors_editors_names,
    publisher_school,
    journal_name,
    year_of_publication,
    volume,
    pages_free_text,
    category,
    language,
    tracking_records,
    record_action,
    related_citations,
    staff_notes,
    record_history,
    dataset,
    created_date,
    modified_date,
]
