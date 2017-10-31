from isisdata.models import *
from django.utils.text import slugify

import export

import functools

def create_acr_string(author, additional_fields = []):
    fields = ['ACR_ID ' + str(author[0]),
               'ACRStatus ' + str(author[1]) if author[1] else u'',
               'ACRType ' + dict(ACRelation.TYPE_CHOICES)[author[2]] if author[2] else u'',
               'ACRDisplayOrder ' + str(author[3]) if author[3] else u'',
               'ACRNameForDisplayInCitation ' + author[4] if author[4] else u'',
               'CitationID ' + str(author[5]) if author[5] else u'',
               'AuthorityStatus ' + str(author[6]) if author[6] else u'',
               'AuthorityType ' + dict(Authority.TYPE_CHOICES)[author[7]] if author[7] else u'',
               'AuthorityName ' + author[8] if author[8] else u''
                ]
    return u' '.join(fields + [field_name + ' ' + str(author[9+idx]) for idx,field_name in enumerate(additional_fields)])
acr_fields = ['id',
          'record_status_value',
          'type_controlled',
          'data_display_order',
          'name_for_display_in_citation',
          'citation__id',
          'authority__record_status_value',
          'authority__type_controlled',
          'authority__name'
         ]

def _redirect(obj, extra):
    if not obj.redirect_to:
        return u""

    return obj.redirect_to.id

def _last_name(obj, extra):
    if obj.type_controlled == Authority.PERSON:
        try:
            person = Person.objects.get(pk=obj.id)
            return person.personal_name_last
        except:
            print "No person record"
            return u""
    return u""

def _first_name(obj, extra):
    if obj.type_controlled == Authority.PERSON:
        try:
            person = Person.objects.get(pk=obj.id)
            return person.personal_name_first
        except:
            print "No person record"
            return u""
    return u""

def _name_suffix(obj, extra):
    if obj.type_controlled == Authority.PERSON:
        try:
            person = Person.objects.get(pk=obj.id)
            return person.personal_name_suffix
        except:
            print "No person record"
            return u""
    return u""

def _name_preferred(obj, extra):
    if obj.type_controlled == Authority.PERSON:
        try:
            person = Person.objects.get(pk=obj.id)
            return person.personal_name_preferred
        except:
            print "No person record"
            return u""
    return u""

def _attributes(obj, extra):
    qs = obj.attributes.all()

    if qs.count() > 0:
        return u' // '.join(map(lambda x: u' '.join(['Attribute_ID ' + x.id, 'Status ' + x.record_status_value, 'Type ' + x.type_controlled.name, 'Value ' + str(x.value.cvalue()), 'FreeFormValue ' + x.value_freeform, 'Description ' + x.description]), qs))

    return u""

def _linked_data(obj, extra):
    """
    Get linked data entries
    """
    qs = obj.linkeddata_entries.all()
    if qs.count() == 0:
        return u''

    return u' // '.join(map(lambda x: u' '.join(['LinkedData_ID ' + x[0], 'Status ' + x[1], 'Type ' + x[2], 'URN ' + x[3], 'ResourceName ' + x[4], 'URL ' + x[5]]), qs.values_list(*['id', 'record_status_value', 'type_controlled__name', 'universal_resource_name', 'resource_name', 'url'])))

def _related_authorities(obj, extra):
    qs = obj.acrelation_set.all()
    return u' // '.join(map(create_acr_string, qs.values_list(*acr_fields)))


redirect = export.Column(u'Redirect', _redirect)
name = export.Column(u'Name', lambda obj, extra: obj.name)
description = export.Column(u'Description', lambda obj, extra: obj.description)
classification_system = export.Column(u'Classification System', lambda obj, extra: obj.get_classification_system_display())
last_name = export.Column(u"Last Name", _last_name)
first_name = export.Column(u"First Name", _first_name)
name_suffix = export.Column(u"Name Suffix", _name_suffix)
name_preferred = export.Column(u"Name Preferred", _name_preferred)
attributes = export.Column(u"Attributes", _attributes)
linked_data = export.Column(u"Linked Data", _linked_data)
related_authorities = export.Column(u"Related Authorities", _related_authorities)


AUTHORITY_COLUMNS = [
    export.object_id,
    export.record_type,
    export.record_nature,
    redirect,
    name,
    description,
    classification_system,
    export.record_history,
    last_name,
    first_name,
    name_suffix,
    name_preferred,
    attributes,
    linked_data,
    related_authorities,
]
