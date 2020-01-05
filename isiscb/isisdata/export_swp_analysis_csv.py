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


object_id = export_item_count_csv.Column(u'Record number', lambda obj, extra, config={}: obj.id)
print_status = export_item_count_csv.Column(u'Print status', export_item_count_csv._print_status)
record_status = export_item_count_csv.Column(u'Record Status', lambda obj, extra, config={}: obj.get_record_status_value_display())
citation_title = export_item_count_csv.Column(u'Title', export_item_count_csv._citation_title, Citation)
record_type = export_item_count_csv.Column('Record Type', export_item_count_csv._record_type)
authors_editors_names = export_item_count_csv.Column('Author/Editor Names', _authors_editors_names)

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

    tracking_records,
    record_action,
    related_citations,
    staff_notes,
    record_history,
    dataset,
    created_date,
    modified_date,
]
