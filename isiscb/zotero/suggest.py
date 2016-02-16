from django.db.models import Q

from isisdata.models import *
from zotero.models import *

import difflib
from collections import Counter, defaultdict


def argsort(seq):
    seq = list(seq)
    return sorted(range(len(seq)), key=seq.__getitem__)


def aggregate_hits(hits):
    """
    Combine individual hits into a condensed set of suggestions and reasons.
    """
    uniqueHits = Counter()
    uniqueReasons = defaultdict(list)
    for hit, basis, value, match in hits:
        if match > uniqueHits[hit]:
            uniqueHits[hit] = match
        uniqueReasons[hit].append((basis, value))

    return [{
                'id': uniqueHits.keys()[k],
                'match': uniqueHits[uniqueHits.keys()[k]],
                'reasons': uniqueReasons[uniqueHits.keys()[k]]
            } for k in argsort(uniqueHits.values())[::-1]]


def suggest_by_attributes(draftObject):
    hits = []
    for attribute in draftObject.attributes.all():
        attrTypes = AttributeType.objects.filter(name__icontains=attribute.name)
        for attrType in attrTypes:
            exact_match = attrType.attribute_set.filter(value__value=attribute.value)
            hits += [(attr.subject_instance_id, 'Attribute', attr.id, 1.0) for attr in exact_match]
    return hits


def suggest_by_linkeddata(draftObject):
    """
    Attempt to match an object based on associated linkeddata values.
    """
    hits = []
    for linkeddata in draftObject.linkeddata.all():
        ldTypes = LinkedDataType.objects.filter(name__icontains=linkeddata.name)
        for ldType in ldTypes:
            exact_match = ldType.linkeddata_set.filter(universal_resource_name__icontains=linkeddata.value)
            hits += [(ldatum.subject_instance_id, 'LinkedData', ldatum.id, 1.0) for ldatum in exact_match]

        inexact_match = LinkedData.objects.filter(
           Q(universal_resource_name__icontains=linkeddata.value) |
           Q(universal_resource_name__in=linkeddata.value))
        if inexact_match.count() <= 10:
            for ldatum in inexact_match:
                match = difflib.SequenceMatcher(None, ldatum.universal_resource_name, linkeddata.value).real_quick_ratio()
                if match > 0.6:
                    hits.append((ldatum.subject_instance_id, 'LinkedData', ldatum.id, match))

    return hits


def suggest_by_field(draftObject, field, targetModel, targetField):
    """
    Attempt to match an object based on an arbitrary field.
    """
    hits = []
    value = getattr(draftObject, field)

    inexact_match = targetModel.objects.filter(
        Q(**{'{0}__icontains'.format(targetField): value}) |
        Q(**{'{0}__in'.format(targetField): value}))

    for obj in inexact_match:
        targetValue = getattr(obj, targetField)
        match = difflib.SequenceMatcher(None, value, targetValue).real_quick_ratio()
        if match > 0.6:
            hits.append((obj.id, 'field', targetField, match))
    return hits


def suggest_citation(draftCitation):
    hits = []
    hits += suggest_by_linkeddata(draftCitation)
    hits += suggest_by_field(draftCitation, 'title', Citation, 'title')
    return aggregate_hits(hits)


def suggest_authority(draftAuthority):
    hits = []
    hits += suggest_by_linkeddata(draftAuthority)
    # hits += suggest_by_attributes(draftAuthority)
    hits += suggest_by_field(draftAuthority, 'name', Authority, 'name')
    return aggregate_hits(hits)


def suggest_citations(queryset):
    for obj in queryset:
        print suggest_citation(obj)


def suggest_authorities(queryset):
    for obj in queryset:
        print suggest_authority(obj)
