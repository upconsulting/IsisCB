from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from builtins import map
from builtins import str
from isisdata.models import *
from django.utils.text import slugify

from . import export

import functools

def create_acr_string(author, additional_fields = []):
    fields = ['ACR_ID ' + str(author[0]),
               'ACRStatus ' + (str(author[1]) if author[1] else u''),
               'ACRType ' + (dict(ACRelation.TYPE_CHOICES)[author[2]] if author[2] else u''),
               'ACRDisplayOrder ' + (str(author[3]) if author[3] else u''),
               'ACRNameForDisplayInCitation ' + (author[4] if author[4] else u''),
               'CitationID ' + (str(author[5]) if author[5] else u''),
               'CitationStatus ' + (str(author[6]) if author[6] else u''),
               'CitationType ' + (dict(Citation.TYPE_CHOICES)[author[7]] if author[7] else u''),
               'CitationTitle ' + (author[8] if author[8] else u'')
                ]
    return u' || '.join(fields + [field_name + ' ' + str(author[9+idx]) for idx,field_name in enumerate(additional_fields)])
acr_fields = ['id',
          'record_status_value',
          'type_controlled',
          'data_display_order',
          'name_for_display_in_citation',
          'citation__id',
          'citation__record_status_value',
          'citation__type_controlled',
          'citation__title'
         ]

def _redirect(obj, extra, config={}):
    if not obj.redirect_to:
        return u""

    return obj.redirect_to.id

def _last_name(obj, extra, config={}):
    if obj.type_controlled == Authority.PERSON:
        try:
            person = Person.objects.get(pk=obj.id)
            return person.personal_name_last
        except:
            print("No person record")
            return u""
    return u""

def _first_name(obj, extra, config={}):
    if obj.type_controlled == Authority.PERSON:
        try:
            person = Person.objects.get(pk=obj.id)
            return person.personal_name_first
        except:
            print("No person record")
            return u""
    return u""

def _name_suffix(obj, extra, config={}):
    if obj.type_controlled == Authority.PERSON:
        try:
            person = Person.objects.get(pk=obj.id)
            return person.personal_name_suffix
        except:
            print("No person record")
            return u""
    return u""

def _name_preferred(obj, extra, config={}):
    if obj.type_controlled == Authority.PERSON:
        try:
            person = Person.objects.get(pk=obj.id)
            return person.personal_name_preferred
        except:
            print("No person record")
            return u""
    return u""

def _attributes(obj, extra, config={}):
    qs = obj.attributes.all()

    def create_value_list(x):
        start, end = '', ''
        if isinstance(x.value.cvalue(), list):
            if len(x.value.cvalue()) > 0:
                start = ', '.join([str(y) for y in x.value.cvalue()[0]]) if isinstance(x.value.cvalue()[0], list) else str(x.value.cvalue()[0])
            if len(x.value.cvalue()) > 1:
                end = ', '.join([str(y) for y in x.value.cvalue()[1]]) if isinstance(x.value.cvalue()[1], list) else str(x.value.cvalue()[1])

        return ['AttributeID ' + x.id,
            'AttributeStatus ' + (x.record_status_value if x.record_status_value else ''),
            'AttributeType ' + x.type_controlled.name,
            'AttributeValue ' + (str(x.value.cvalue()) if x.value and x.value.cvalue() else ''),
            'AttributeFreeFormValue ' + (x.value_freeform if x.value_freeform else ''),
            'AttributeStart ' + start,
            'AttributeEnd ' + end,
            'AttributeDescription ' + (x.description if x.description else '')]

    if qs.count() > 0:
        return u' // '.join([u' || '.join(create_value_list(x)) for x in qs])

    return u""

def _linked_data(obj, extra, config={}):
    """
    Get linked data entries
    """
    qs = obj.linkeddata_entries.all()
    if qs.count() == 0:
        return u''

    return u' // '.join([u' || '.join(['LinkedData_ID ' + (x[0] if x[0] else ''), 'Status ' + (x[1] if x[1] else ''), 'Type ' + (x[2] if x[2] else ''), 'URN ' + (x[3] if x[3] else ''), 'ResourceName ' + (x[4] if x[4] else ''), 'URL ' + (x[5] if x[5] else '')]) for x in qs.values_list(*['id', 'record_status_value', 'type_controlled__name', 'universal_resource_name', 'resource_name', 'url'])])

def _related_citations(obj, extra, config={}):
    qs = obj.acrelation_set.all()
    return u' // '.join(map(create_acr_string, qs.values_list(*acr_fields)))

def _related_citations_count(obj, extra, config={}):
    qs = obj.acrelation_set.all()
    return str(qs.count())

redirect = export.Column(u'Redirect', _redirect)
name = export.Column(u'Name', lambda obj, extra, config={}: obj.name)
description = export.Column(u'Description', lambda obj, extra, config={}: obj.description)
classification_system = export.Column(u'Classification System', lambda obj, extra, config={}: obj.get_classification_system_display())
classification_code = export.Column(u'Classification Code', lambda obj, extra, config={}: obj.classification_code)
last_name = export.Column(u"Last Name", _last_name)
first_name = export.Column(u"First Name", _first_name)
name_suffix = export.Column(u"Name Suffix", _name_suffix)
name_preferred = export.Column(u"Name Preferred", _name_preferred)
attributes = export.Column(u"Attributes", _attributes)
linked_data = export.Column(u"Linked Data", _linked_data)
related_citations = export.Column(u"Related Citations", _related_citations)
related_citations_count = export.Column(u"Related Citations Count", _related_citations_count)
creator = export.Column(u"Creator", lambda obj, extra, config={}: obj.created_by_stored.first_name + " " + obj.created_by_stored.last_name + " (" + obj.created_by_stored.username + ")")


AUTHORITY_COLUMNS = [
    export.object_id,
    export.record_type,
    export.record_nature,
    redirect,
    name,
    description,
    classification_system,
    classification_code,
    last_name,
    first_name,
    name_suffix,
    name_preferred,
    attributes,
    linked_data,
    related_citations,
    related_citations_count,
    export.staff_notes,
    export.record_history,
    export.created_on,
    export.modified_on,
    creator,
    export.modifier,

]
