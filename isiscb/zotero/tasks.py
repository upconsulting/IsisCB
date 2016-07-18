from isisdata.models import *
from zotero.models import *

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

    if not accession.resolved:
        raise RuntimeError('Cannot ingest an ImportAccession with unresolved' \
                         + ' DraftAuthority records')

    ingested = []
    for draftcitation in accession.draftcitation_set.filter(processed=False):
        try:
            ingested.append(ingest_citation(request, accession, draftcitation))
        except Exception as E:
            print E
    accession.processed = True
    accession.save()

    return ingested


def ingest_citation(request, accession, draftcitation):
    # If the citation is already resolved, there is nothing to do here: we
    #  simply return the target of the resolution.
    if draftcitation.resolutions.count() > 0:
        return draftcitation.resolutions.first()

    if not accession.resolved:
        raise RuntimeError('Accession not resolved')

    citation_fields = [
        ('title', 'title'),
        ('description', 'description'),
        ('abstract', 'abstract'),
        ('type_controlled', 'type_controlled'),
    ]
    partdetails_fields = [
        ('page_start', 'page_begin'),
        ('page_end', 'page_end'),
        ('pages_free_text', 'pages_free_text'),
        ('issue', 'issue_free_text'),
        ('volume', 'volume_free_text'),
    ]
    int_only_fields = dict([
        ('page_start', 'pages_free_text'),
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

    # Records are inactive/non-public by default. The record_history message
    #  provides information about the Zotero accession.
    citation_data.update({
        '_history_user': request.user,
        'public': False,
        'record_status_value': CuratedMixin.INACTIVE,
        'record_status_explanation': u'Inactive by default',
        'record_history': _record_history_message(request, accession),
        'belongs_to': accession.ingest_to,
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

    date = None
    if draftcitation.publication_date:
        if type(draftcitation.publication_date) in [str, unicode]:
            try:
                date = iso8601.parse_date(draftcitation.publication_date).date()
            except iso8601.ParseError:
                date = None
        elif type(draftcitation.publication_date) is datetime.datetime:
            date = draftcitation.publication_date.date()

    if date:
        citation.publication_date = date

        pubdatetype = AttributeType.objects.get(name='PublicationDate')
        attribute = Attribute.objects.create(
            type_controlled=pubdatetype,
            source=citation,
            value_freeform=draftcitation.publication_date
        )
        vvalue = ISODateValue.objects.create(
            value=date,
            attribute=attribute,
        )

    for relation in draftcitation.authority_relations.all():
        draft = relation.authority
        target = draft.resolutions.first().to_instance
        target.zotero_accession = accession
        target.save()

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
        }
        acrelation = ACRelation.objects.create(**acr_data)

        InstanceResolutionEvent.objects.create(
            for_instance = relation,
            to_instance = acrelation,
        )


    for draftlinkeddata in draftcitation.linkeddata.all():
        ldtype, _ = LinkedDataType.objects.get_or_create(name=draftlinkeddata.name)
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
