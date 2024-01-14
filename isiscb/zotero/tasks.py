"""
These functions are mostly related to transitioning data from the Zotero app
to the IsisData app.

TODO: many of these functions could use refactoring, or at least modularizing
for easier testing.
"""
from __future__ import unicode_literals

from django.db.models import Q

from isisdata.models import *
from zotero.models import *
import curation.curation_util as curation_util

import iso8601


def _record_history_message(request, accession):
    template = u'Created from Zotero accession {0}, performed at {1} by {2}.' \
             + u' Subsequently ingested by {3}.'
    values = (
        accession.id,
        accession.imported_on,
        accession.imported_by,
        request.user.username
    )
    return template.format(*values)


def ingest_accession(request, accession):
    """
    Move all constituents of an :class:`.ImportAccession` into the production
    database.
    """

    ingested = []    # These will be production Citation instances.
    ingested_draft_ids = []    # These will be DraftCitation ids.
    for draftcitation in accession.citations_ok:
        ingested.append(ingest_citation(request, accession, draftcitation))
        ingested_draft_ids.append(draftcitation.id)
    ingest_ccrelations(request, accession, ingested_draft_ids)

    if accession.citations_remaining.count() == 0:
        accession.processed = True
        accession.save()

    return ingested


def ingest_citation(request, accession, draftcitation):
    # If the citation is already resolved, there is nothing to do here: we
    #  simply return the target of the resolution.
    if draftcitation.resolutions.count() > 0:
        return draftcitation.resolutions.first().to_instance

    citation_fields = [
        ('title', 'title'),
        ('description', 'description'),
        ('abstract', 'abstract'),
        ('type_controlled', 'type_controlled'),
        ('book_series', 'book_series'),
        ('physical_details', 'physical_details')
    ]
    partdetails_fields = [
        ('page_start', 'page_begin'),
        ('page_end', 'page_end'),
        ('pages_free_text', 'pages_free_text'),
        ('issue', 'issue_free_text'),
        ('volume', 'volume_free_text'),
        ('extent', 'extent'),
        ('extent_note', 'extent_note'),
    ]
    int_only_fields = dict([
        ('page_start', 'pages_free_text'),
        ('page_begin', 'pages_free_text'),
        ('page_end', 'pages_free_text'),
        ('extent', 'extent_note'),
    ])

    # Gather fields that will be transferred to the production Citation.
    citation_data = {}
    for field, pfield in citation_fields:
        value = getattr(draftcitation, field, None)
        if value:
            if field in int_only_fields:
                try:
                    value = int(value)
                except ValueError:      # Not an int!'
                    citation_data[int_only_fields[pfield]] = value
                    continue
            citation_data[pfield] = value

    tenant = curation_util.get_tenant(request.user)
    if tenant:
        citation_data.update({
            'owning_tenant': tenant
        })

    # Records are inactive/non-public by default. The record_history message
    #  provides information about the Zotero accession.
    citation_data.update({
        '_history_user': request.user,
        'public': False,
        'record_status_value': CuratedMixin.INACTIVE,
        'record_status_explanation': u'Inactive by default',
        'record_history': _record_history_message(request, accession),
        'belongs_to': accession.ingest_to if accession.ingest_to else (tenant.default_dataset if tenant else None),
        'zotero_accession': accession,
    })

    # Troll for data for PartDetails fields.
    partdetails_data = {}
    for field, pfield in partdetails_fields:
        value = getattr(draftcitation, field)
        if value:
            if field in int_only_fields:
                try:
                    value = int(value)
                except ValueError:      # Not an int!
                    partdetails_data[int_only_fields[pfield]] = value
                    continue
            partdetails_data[pfield] = value

    if partdetails_data:
        partdetails = PartDetails.objects.create(**partdetails_data)
        citation_data.update({'part_details': partdetails})

    citation = Citation.objects.create(**citation_data)
    InstanceResolutionEvent.objects.create(for_instance=draftcitation, to_instance=citation)

    # ISISCB-749 Language should be preserved from Zotero records.
    if draftcitation.language:
        citation.language.add(draftcitation.language)

    date = None
    if draftcitation.publication_date:
        if type(draftcitation.publication_date) in [str, str]:
            try:
                date = iso8601.parse_date(draftcitation.publication_date).date()
            except iso8601.ParseError:
                match = re.search('([0-9]{4})', draftcitation.publication_date)
                if match:
                    date = match.groups()[0]
                else:
                    date = None
        elif type(draftcitation.publication_date) is datetime.datetime:
            date = draftcitation.publication_date.date()

    if date:
        if type(date) in [str, str]:
            date = iso8601.parse_date(date).date()
        citation.publication_date = date
        pubdatetype, _ = AttributeType.objects.get_or_create(
            name='PublicationDate',
            defaults={
                'value_content_type': ContentType.objects.get_for_model(ISODateValue)
            })
        if type(date) in [datetime.datetime, datetime.date]:
            value_freeform = date.year
        elif type(date) in [str, str]:
            value_freeform = date[:4]
        attribute = Attribute.objects.create(
            type_controlled=pubdatetype,
            source=citation,
            value_freeform=value_freeform
        )
        vvalue = ISODateValue.objects.create(
            value=date,
            attribute=attribute,
        )

    elif draftcitation.publication_date:
        # If we cannot parse the publication date as an ISO8601 date, then we
        #  update the staff notes with the unparseable date so that it is not
        #  completely lost.
        message=  u'\nCould not parse publication date in Zotero metadata: %s'\
                  % draftcitation.publication_date
        if citation.administrator_notes:
            citation.administrator_notes += message
        else:
            citation.administrator_notes = message
        citation.save()

    for relation in draftcitation.authority_relations.all():
        draft = relation.authority
        try:
            target = draft.resolutions.first().to_instance
        except AttributeError:    # No resolution target. We create a "headless"
            target = None         #  ACRelation.
            citation.record_history += u"\n\nThe attempt to match the name %s in the %s field was skipped." % (draft.name, relation.get_type_controlled_display())
            citation.save()

        if target:
            target.zotero_accession = accession
            target.save()

            # Transfer any linkeddata from the DraftAuthority to the production
            #  Authority.
            for draftlinkeddata in draft.linkeddata.all():
                ldtype, _ = LinkedDataType.objects.get_or_create(name=draftlinkeddata.name.upper())
                if not target.linkeddata_entries.filter(type_controlled=ldtype, universal_resource_name=draftlinkeddata.value):
                    LinkedData.objects.create(
                        subject = target,
                        universal_resource_name = draftlinkeddata.value,
                        type_controlled = ldtype
                    )
            draft.linkeddata.all().update(processed=True)

        # ISISCB-577 Created ACRelation records should be active by default.
        acr_data = {
            '_history_user': request.user,
            'name_for_display_in_citation': draft.name,
            'record_history': _record_history_message(request, accession),
            'public': True,
            'record_status_value': CuratedMixin.ACTIVE,
            'record_status_explanation': u'Active by default',
            'authority': target,
            'citation': citation,
            'type_controlled': relation.type_controlled,
            'belongs_to': accession.ingest_to,
            'zotero_accession': accession,
            'data_display_order': relation.data_display_order,
        }
        acrelation = ACRelation.objects.create(**acr_data)

        InstanceResolutionEvent.objects.create(
            for_instance = relation,
            to_instance = acrelation,
        )

    ld_created = set([])
    for linkeddata in citation.linkeddata_entries.all():
        ld_created.add(linkeddata.universal_resource_name)

    for draftlinkeddata in draftcitation.linkeddata.all():
        _key = draftlinkeddata.value
        if _key in ld_created:
            continue
        ld_created.add(_key)
        ldtype, _ = LinkedDataType.objects.get_or_create(name=draftlinkeddata.name.upper())
        LinkedData.objects.create(
            subject = citation,
            universal_resource_name = draftlinkeddata.value,
            type_controlled = ldtype
        )
    draftcitation.linkeddata.all().update(processed=True)

    draftcitation.authority_relations.all().update(processed=True)

    draftcitation.processed = True
    draftcitation.save()

    accession.save()

    return citation


def ingest_ccrelations(request, accession, ingested):
    """
    Ingest :class:`.DraftCCRelation` instances among "ready"
    :class:`.DraftCitation`\s.

    Parameters
    ----------
    request
    accession : :class:`.ImportAccession`
    ingested : list
        List of :class:`.DraftCitation` ids.

    Returns
    -------
    None
    """

    # Both source and target must be ingested, and no other resolution for this
    #  DraftCCRelation may exist.
    query = Q(subject_id__in=ingested) & Q(object_id__in=ingested) & Q(resolutions=None)
    for relation in accession.draftccrelation_set.filter(query):
        draft_source = relation.subject
        source = ingest_citation(request, accession, draft_source)    # Get.
        draft_target = relation.object
        target = ingest_citation(request, accession, draft_target)

        ccr_data = {
            '_history_user': request.user,
            'public': True,
            'record_history': _record_history_message(request, accession),
            'record_status_value': CuratedMixin.ACTIVE,
            'record_status_explanation': u'Active by default',
            'subject': source,
            'object': target,
            'type_controlled': relation.type_controlled,
            'belongs_to': accession.ingest_to,
            'zotero_accession': accession,
        }
        ccrelation = CCRelation.objects.create(**ccr_data)
        InstanceResolutionEvent.objects.create(
            for_instance = relation,
            to_instance = ccrelation,
        )
