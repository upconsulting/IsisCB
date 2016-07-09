from isisdata.models import *
from zotero.models import *


def ingest_accession(request, accession):
    """
    Move all constituents of an :class:`.ImportAccession` into the production
    database.
    """

    if not accession.resolved:
        raise RuntimeError('Cannot ingest an ImportAccession with unresolved DraftAuthority records')



def ingest_citation(request, accession, draftcitation):
    if draftcitation.resolutions.count() > 0:
        return draftcitation.resolutions.first()

    citation_fields = [
        'title',
        'description',
        'abstract',
        'type_controlled'
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

    citation_data = {}
    for field, pfield in citation_fields:
        value = getattr(draftcitation, field)
        if value:
            if field in int_only_fields:
                try:
                    value = int(value)
                except ValueError:      # Not an int!
                    citation_data[int_only_fields[pfield]] = value
                    continue
            citation_data[pfield] = value

    citation_date.update({
        'public': False,
        'record_status_value': CuratedMixin.INACTIVE,
        'record_history': u'Created from Zotero accession {0}, performed at {1} by {2}. Subsequently ingested by {3}.'.format(accession.id, accession.imported_on, accession.imported_by, request.user.username),

    })

    partdetails_data = {}
    for field, pfield in partdetails_fields:
        value = getattr(draftcitation, field)
        if value:
            pif field in int_only_fields:
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

    if draftcitation.publication_date:
        pubdatetype = AttributeType.objects.get(name='PublicationDate')
        attribute = Attribute.objects.create(
            type_controlled=pubdatetype,
            source=citation,
            value_freeform=draftcitation.publication_date
        )
        vvalue = IsoDateValue.objects.create(
            value=draftcitation.publication_date,
            attribute=attribute,
        )
