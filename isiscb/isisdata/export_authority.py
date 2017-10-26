from isisdata.models import *
from django.utils.text import slugify

import export

import functools

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

redirect = export.Column(u'Redirect', _redirect)
name = export.Column(u'Name', lambda obj, extra: obj.name)
description = export.Column(u'Description', lambda obj, extra: obj.description)
classification_system = export.Column(u'Classification System', lambda obj, extra: obj.get_classification_system_display())
last_name = export.Column(u"Last Name", _last_name)
first_name = export.Column(u"First Name", _first_name)
name_suffix = export.Column(u"Name Suffix", _name_suffix)
name_preferred = export.Column(u"Name Preferred", _name_preferred)


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
]
