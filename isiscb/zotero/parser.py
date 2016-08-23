import os, re, iso8601, rdflib, codecs, chardet, unicodedata, logging, csv
import xml.etree.ElementTree as ET

from datetime import datetime

from models import *
from isisdata.models import Authority, Citation, ACRelation, LinkedData, LinkedDataType


subjectIDMap = {}
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../AuthorityIDmap.tab'), 'rU') as f:
    reader = csv.reader(f, delimiter='\t')
    for row in reader:
        subjectIDMap[int(row[1])] = row[0]


# rdflib complains a lot.
logging.getLogger("rdflib").setLevel(logging.ERROR)

# RDF terms.
RDF = u'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
DC = u'http://purl.org/dc/elements/1.1/'
FOAF = u'http://xmlns.com/foaf/0.1/'
PRISM = u'http://prismstandard.org/namespaces/1.2/basic/'
RSS = u'http://purl.org/rss/1.0/modules/link/'
BIBLIO = u'http://purl.org/net/biblio#'
ZOTERO = u'http://www.zotero.org/namespaces/export#'

URI_ELEM = rdflib.URIRef("http://purl.org/dc/terms/URI")
TYPE_ELEM = rdflib.term.URIRef(RDF + u'type')
VALUE_ELEM = rdflib.URIRef(RDF + u'value')
LINK_ELEM = rdflib.URIRef(RSS + u"link")
FORENAME_ELEM = rdflib.URIRef(FOAF + u'givenname')
SURNAME_ELEM = rdflib.URIRef(FOAF + u'surname')
VOL = rdflib.term.URIRef(PRISM + u'volume')
ISSUE = rdflib.term.URIRef(PRISM + u'number')
IDENT = rdflib.URIRef(DC + u"identifier")
TITLE = rdflib.term.URIRef(DC + u'title')
SUBJECT = rdflib.URIRef(DC + u"subject")


BOOK = rdflib.term.URIRef(BIBLIO + 'Book')
ZBOOK = rdflib.term.URIRef(ZOTERO + 'Book')
JOURNAL = rdflib.term.URIRef(BIBLIO + 'Journal')
WEBSITE = rdflib.term.URIRef(ZOTERO + 'Website')

REVIEWED_AUTHORS = rdflib.term.URIRef(ZOTERO + 'reviewedAuthors')

# TODO: We don't have the right relation types to support WEBSITE yet!
PARTOF_TYPES = [
    (ZBOOK, 'book'),
    (BOOK, 'book'),
    (JOURNAL, 'journal'),
]



class dobject(object):
    pass


class Paper(object):
    pass


def _cast(value):
    """
    Attempt to convert ``value`` to an ``int`` or ``float``. If unable, return
    the value unchanged.
    """

    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


class BaseParser(object):
    """
    Base class for all data parsers. Do not instantiate directly.
    """

    def __init__(self, path, **kwargs):
        self.path = path
        self.data = []
        self.fields = set([])

        for k, v in kwargs.items():
            setattr(self, k, v)

        self.open()


    def new_entry(self):
        """
        Prepare a new data entry.
        """
        self.data.append(self.entry_class())

    def _get_handler(self, tag):
        handler_name = 'handle_{tag}'.format(tag=tag)
        if hasattr(self, handler_name):
            return getattr(self, handler_name)
        return

    def set_value(self, tag, value):
        setattr(self.data[-1], tag, value)

    def postprocess_entry(self):
        for field in self.fields:
            processor_name = 'postprocess_{0}'.format(field)
            if hasattr(self.data[-1], field) and hasattr(self, processor_name):
                getattr(self, processor_name)(self.data[-1])

        if hasattr(self, 'reject_if'):
            if self.reject_if(self.data[-1]):
                del self.data[-1]


class IterParser(BaseParser):
    entry_class = dobject
    """Model for data entry."""

    concat_fields = []
    """
    Multi-line fields here should be concatenated, rather than represented
    as lists.
    """

    tags = {}

    def __init__(self, *args, **kwargs):
        super(IterParser, self).__init__(*args, **kwargs)

        self.current_tag = None
        self.last_tag = None

        if kwargs.get('autostart', True):
            self.start()

    def parse(self):
        """

        """
        while True:        # Main loop.
            tag, data = self.next()
            if self.is_eof(tag):
                self.postprocess_entry()
                break

            self.handle(tag, data)
            self.last_tag = tag
        return self.data

    def start(self):
        """
        Find the first data entry and prepare to parse.
        """

        while not self.is_start(self.current_tag):
            self.next()
        self.new_entry()

    def handle(self, tag, data):
        """
        Process a single line of data, and store the result.

        Parameters
        ----------
        tag : str
        data :
        """

        if isinstance(data,unicode):
            data = unicodedata.normalize('NFKD', data)#.encode('utf-8','ignore')

        if self.is_end(tag):
            self.postprocess_entry()

        if self.is_start(tag):
            self.new_entry()

        if data is None or tag is None:
            return

        handler = self._get_handler(tag)
        if handler is not None:
            data = handler(data)

        if tag in self.tags:    # Rename the field.
            tag = self.tags[tag]

        # Multiline fields are represented as lists of values.
        if hasattr(self.data[-1], tag):
            value = getattr(self.data[-1], tag)

            if tag in self.concat_fields:
                value = ' '.join([value, unicode(data)])
            elif type(value) is list:
                if type(data) is list:
                    value += data
                else:
                    value.append(data)
            elif value not in [None, '']:
                value = [value, data]
        else:
            value = data
        setattr(self.data[-1], tag, value)
        self.fields.add(tag)


class RDFParser(BaseParser):
    entry_elements = ['Document']
    meta_elements = []
    concat_fields = []

    def open(self):
        self.graph = rdflib.Graph()
        self.graph.parse(self.path)
        self.entries = []

        for element in self.entry_elements:
            query = 'SELECT * WHERE { ?p a ' + element + ' }'
            self.entries += [r[0] for r in self.graph.query(query)]

    def next(self):
        if len(self.entries) > 0:
            return self.entries.pop(0)

    def parse(self):
        meta_fields, meta_refs = zip(*self.meta_elements)

        while True:        # Main loop.
            entry = self.next()
            if entry is None:
                break

            self.new_entry()

            for s, p, o in self.graph.triples((entry, None, None)):
                if p in meta_refs:  # Look for metadata fields.
                    tag = meta_fields[meta_refs.index(p)]
                    self.handle(tag, o)
            self.postprocess_entry()

        return self.data

    def handle(self, tag, data):
        handler = self._get_handler(tag)

        if handler is not None:
            data = handler(data)

        if tag in self.tags:    # Rename the field.
            tag = self.tags[tag]

        if data is not None:

            # Multiline fields are represented as lists of values.
            if hasattr(self.data[-1], tag):
                value = getattr(self.data[-1], tag)
                if tag in self.concat_fields:
                    value = ' '.join([value, data])
                elif type(value) is list:
                    if type(data) is list:
                        value += data
                    else:
                        value.append(data)
                elif value not in [None, '']:
                    if type(data) is list:
                        value = [value] + data
                    else:
                        value = [value, data]
            else:
                value = data

            setattr(self.data[-1], tag, value)
            self.fields.add(tag)


class ZoteroParser(RDFParser):
    """
    Reads Zotero RDF files.
    """

    entry_class = Paper
    entry_elements = ['bib:Illustration', 'bib:Recording', 'bib:Legislation',
                      'bib:Document', 'bib:BookSection', 'bib:Book', 'bib:Data',
                      'bib:Letter', 'bib:Report', 'bib:Article',
                      'bib:Manuscript', 'bib:Image',
                      'bib:ConferenceProceedings', 'bib:Thesis']

    document_type_default = 'AR'
    document_types = {
        'journalArticle': 'AR',
        'book': 'BO',
        'thesis': 'TH',
        'bookSection': 'CH',
        'webpage': 'WE',
    }
    tags = {
        # 'isPartOf': 'journal'
    }

    meta_elements = [
        ('date', rdflib.URIRef("http://purl.org/dc/elements/1.1/date")),
        ('identifier',
         rdflib.URIRef("http://purl.org/dc/elements/1.1/identifier")),
        ('subjects', rdflib.URIRef("http://purl.org/dc/terms/subject")),
        ('subjects', rdflib.URIRef("http://purl.org/dc/elements/1.1/subject")),
        ('abstract', rdflib.URIRef("http://purl.org/dc/terms/abstract")),
        ('authors_full', rdflib.URIRef("http://purl.org/net/biblio#authors")),
        ('seriesEditors',
         rdflib.URIRef("http://www.zotero.org/namespaces/export#seriesEditors")),
        ('editors', rdflib.URIRef("http://purl.org/net/biblio#editors")),
        ('contributors',
         rdflib.URIRef("http://purl.org/net/biblio#contributors")),
        ('translators',
         rdflib.URIRef("http://www.zotero.org/namespaces/export#translators")),
        ('link', rdflib.URIRef("http://purl.org/rss/1.0/modules/link/link")),
        ('title', rdflib.URIRef("http://purl.org/dc/elements/1.1/title")),
        ('isPartOf', rdflib.URIRef("http://purl.org/dc/terms/isPartOf")),
        ('pages', rdflib.URIRef("http://purl.org/net/biblio#pages")),
        ('documentType',
         rdflib.URIRef("http://www.zotero.org/namespaces/export#itemType")),
        ('review_of', REVIEWED_AUTHORS)]

    reject_if = lambda self, x: not hasattr(x, 'documentType')

    def __init__(self, path, **kwargs):
        # name = os.path.split(path)[1]
        # path = os.path.join(path, '{0}.rdf'.format(name))
        super(ZoteroParser, self).__init__(path, **kwargs)

        self.full_text = {}     # Collect StructuredFeatures until finished.

    def open(self):
        """
        Fixes RDF validation issues. Zotero incorrectly uses ``rdf:resource`` as
        a child element for Attribute; ``rdf:resource`` should instead be used
        as an attribute of ``link:link``.
        """

        with open(self.path, 'r') as f:
            corrected = f.read().replace('rdf:resource rdf:resource',
                                         'link:link rdf:resource')
        with open(self.path, 'w') as f:
            f.write(corrected)

        super(ZoteroParser, self).open()

    def handle_subjects(self, value):
        match = re.match('([^\[]+)\[([A-Z0-9]+)\]', value.toPython())
        if match:
            name, identifier = match.groups()
            return (name.strip(), identifier.strip())
        else:
            return (value.toPython(), None)

    def handle_identifier(self, value):
        """

        """

        identifier = unicode(self.graph.value(subject=value, predicate=VALUE_ELEM))
        ident_type = self.graph.value(subject=value, predicate=TYPE_ELEM)
        if ident_type == URI_ELEM:
            self.set_value('uri', identifier)
        else:
            name, ident_value = tuple(unicode(value).split(' '))
            name = name.lower()
            if name == 'isbn':
                ident_value = ident_value.replace('-', '')
            self.set_value(name, ident_value)


    def handle_link(self, value):
        """
        rdf:link rdf:resource points to the resource described by a record.
        """
        for s, p, o in self.graph.triples((value, None, None)):
            if p == LINK_ELEM:
                return unicode(o).replace('file://', '')

    def handle_date(self, value):
        """
        Attempt to coerce date to ISO8601.
        """
        try:
            return iso8601.parse_date(unicode(value))
        except iso8601.ParseError:
            for datefmt in ("%B %d, %Y", "%Y-%m", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    # TODO: remove str coercion.
                    return datetime.strptime(unicode(value), datefmt).date()
                except ValueError:
                    match = re.search('([0-9]{4})', value)
                    if match:
                        return int(match.groups()[0])
                    return value

    def handle_documentType(self, value):
        """

        Parameters
        ----------
        value

        Returns
        -------
        value.toPython()
        Basically, RDF literals are casted to their corresponding Python data types.
        """
        value = value.toPython()
        if value in self.document_types:
            return self.document_types[value]
        return self.document_type_default

    def handle_authors_full(self, value):
        authors = [self.handle_author(o) for s, p, o
                   in self.graph.triples((value, None, None))]
        authors = [a for a in authors if a is not None]

        return authors

    def handle_abstract(self, value):
        """
        Abstract handler.

        Parameters
        ----------
        value

        Returns
        -------
        abstract.toPython()
        Basically, RDF literals are casted to their corresponding Python data types.
        """
        return value.toPython()

    def handle_title(self, value):
        """
        Title handler
        Parameters
        ----------
        value

        Returns
        -------
        title.toPython()

        """
        return value.toPython()


    def handle_author(self, value):
        forename_iter = self.graph.triples((value, FORENAME_ELEM, None))
        surname_iter = self.graph.triples((value, SURNAME_ELEM, None))
        norm = lambda s: unicode(s).upper().replace('.', '')

        # TODO: DRY this out.
        try:
            forename = norm([e[2] for e in forename_iter][0])
        except IndexError:
            forename = u''

        try:
            surname = norm([e[2] for e in surname_iter][0])
        except IndexError:
            surname = u''

        if surname == u'' and forename == u'':
            return
        if forename == u'':
            surname_parts = [p.strip() for p in surname.split(',')]
            if len(surname_parts) > 1:
                surname = surname_parts[0]
                forename = u' '.join(surname_parts[1:])
        return surname, forename

    def handle_editors(self, value):
        return self.handle_authors_full(value)

    def handle_seriesEditors(self, value):
        return self.handle_authors_full(value)

    def handle_contributors(self, value):
        return self.handle_authors_full(value)

    def handle_translators(self, value):
        return self.handle_authors_full(value)

    def handle_isPartOf(self, value):
        journal = None
        for s, p, o in self.graph.triples((value, None, None)):
            if p == VOL:        # Volume number
                self.set_value('volume', unicode(o))
            elif p == ISSUE:
                self.set_value('issue', unicode(o))
            elif p == IDENT:
                # Zotero (in all of its madness) makes some identifiers, like
                #  DOIs, properties of Journals rather than the Articles to
                #  which they belong. The predicate for these relations
                #  is identifier, and the object contains both the identifier
                #  type and the identifier itself, eg.
                #       "DOI 10.1017/S0039484"
                try:
                    name, ident_value = tuple(unicode(o).split(' '))
                    name = name.lower()
                    if name == 'isbn':
                        self.set_value('partof__identifier',
                                       (name, ident_value.replace('-', '')))
                    else:
                        self.set_value(name, ident_value)
                except ValueError:
                    pass
            elif p == TITLE:
                # This could be a journal, book, website, or other
                #  super-publication to which the current record belongs.
                self.set_value('partof__title', unicode(o))
            elif p == TYPE_ELEM:
                # Indicates the type of super-publication (e.g. Journal, Book).
                #(BOOK, 'DraftCCRelation', 'object', CCRelation.INCLUDES_CHAPTER),
                self.set_value('partof__type', dict(PARTOF_TYPES).get(o, None))

        return journal

    def handle_pages(self, value):
        return tuple(value.split('-'))

    def handle_review_of(self, value):
        """
        IsisCB uses this field to denote reviewed works. "Author" surnames will
        be either production identifiers (e.g. CBB00...) or ISBNs.
        """

        return zip(*self.handle_authors_full(value))[0]


    def postprocess_pages(self, entry):
        if type(entry.pages) not in [tuple, list]:
            start = entry.pages
            end = None
        else:
            try: # ISISCB-395: Skip malformed page numbers.
                start, end = entry.pages
            except ValueError:
                setattr(entry, 'pagesFreeText', entry.pages)
                del entry.pages
                return
        setattr(entry, 'pageStart', start)
        setattr(entry, 'pageEnd', end)
        del entry.pages




def read(path):
    """
    Read bibliographic data from Zotero RDF.

    Parameters
    ----------
    path : str
        Path to the RDF file created by Zotero.

    Returns
    -------
    list
    """

    parser = ZoteroParser(path, follow_links=False)
    papers = parser.parse()

    return papers


def process_authorities(paper, instance):
    """
    Create :class:.`DraftAuthority` and :class:`.DraftACRelation` instances from
    parsed data.

    Parameters
    ----------
    paper : :class:`.Paper`
        Vanilla object representing a single Zotero record, and containing
        parsed data.
    instance : :class:`.ImportAccession`
        The current accession instance.

    Returns
    -------
    tuple
        ``([Authorities], [ACRelations])``

    """

    # The entries below map parsed fields (2nd position) onto values for
    #  Authority.type_controlled and ACRelation.type_controlled
    authority_fields = [
        (Authority.PERSON, ACRelation.AUTHOR, 'authors_full', DraftACRelation, 'citation'),
        (Authority.PERSON, ACRelation.EDITOR, 'editors', DraftACRelation, 'citation'),
        (Authority.PERSON, ACRelation.EDITOR, 'seriesEditors', DraftACRelation, 'citation'),
        (Authority.PERSON, ACRelation.CONTRIBUTOR, 'contributors', DraftACRelation, 'citation'),
        (Authority.PERSON, ACRelation.TRANSLATOR, 'translators', DraftACRelation, 'citation'),
        (Authority.SERIAL_PUBLICATION, ACRelation.PERIODICAL, 'partof__title', DraftACRelation, 'citation'),
        (Authority.CONCEPT, ACRelation.SUBJECT, 'subjects', DraftACRelation, 'citation'),

        # ('DraftACRelation', 'authority', ACRelation.PERIODICAL)),('DraftCCRelation', 'object', CCRelation.INCLUDES_CHAPTER)),
    ]

    draftAuthorities = []
    draftACRelations = []
    relationsSeen = set()    # So that we don't create duplicates.
    for authority_type, acrelation_type, field, relation_model, relation_field in authority_fields:
        if not hasattr(paper, field):
            continue
        field_value = getattr(paper, field)

        # If the target of this relation is a book, then we have no need to
        #  create an Authority or ACRelation here; it will be handled elsewhere.
        if field == 'partof__title':
            if getattr(paper, 'partof__type', None) == 'book':
                continue

        # TODO: make this more DRY.
        if type(field_value) is list and authority_type == 'PE':
            for last, first in field_value:
                entity_name = ('%s %s' % (first, last)).title()
                if (acrelation_type, entity_name) in relationsSeen:
                    continue

                entity = DraftAuthority(
                    name = entity_name,
                    name_last = last.title(),
                    name_first = first.title(),
                    type_controlled = authority_type,
                    part_of = instance,
                )
                entity.save()
                draftAuthorities.append(entity)

                relation = DraftACRelation(
                    authority = entity,
                    type_controlled = acrelation_type,
                    part_of = instance,
                )
                draftACRelations.append(relation)
                relationsSeen.add((acrelation_type, entity_name))

        elif type(field_value) is list and len(field_value) > 0 and type(field_value[0]) is tuple:
            authority_id = None
            authority = None
            for value, ident in field_value:
                if ident:
                    if ident.startswith('C'):   # Native PK id.
                        authority_id = ident
                    else:
                        authority_id = subjectIDMap.get(int(ident), None)
                    try:
                        authority = Authority.objects.get(pk=authority_id)
                    except Authority.DoesNotExist:
                        pass
                else:
                    if value.startswith('='):
                        # * Parse the string: "=340-140=" -> 340, 140
                        match = re.match('=([0-9]+)-([0-9]+)=', value)
                        if match:
                            partA, partB = match.groups()
                            # * Invert the values: 340, 140 -> 140, 340
                            # * Build a new string: 140, 340 -> "140-340"
                            lookup = '-'.join([partB, partA])
                        else:
                            lookup = value.replace('=', '').strip()

                        # * Search for an Authority with that
                        #   classification_code: "140-340" -> CBA000131150
                        authority = Authority.objects.filter(classification_code=lookup).first()
                        if authority is not None:
                            authority_id = authority.id

                            # Even though this originates in a dc.subject field,
                            #  these should be linked as categories.
                            acrelation_type = ACRelation.CATEGORY

                entity_name = getattr(authority, 'name', value)
                if (acrelation_type, entity_name) in relationsSeen:
                    continue

                # Use the Authority's name, if available. Otherwise just use
                #  whatever we found in Zotero.
                entity = DraftAuthority.objects.create(
                    name=entity_name,
                    type_controlled=authority_type,
                    part_of=instance,
                    processed=True if authority else False
                )
                draftAuthorities.append(entity)

                if authority:
                    resolution = InstanceResolutionEvent.objects.create(
                        for_instance=entity,
                        to_instance=authority,
                    )

                relation = DraftACRelation(
                    authority = entity,
                    type_controlled = acrelation_type,
                    part_of = instance,
                )
                draftACRelations.append(relation)
                relationsSeen.add((acrelation_type, entity_name))
        else:
            if type(field_value) is tuple:
                if len([v for v in field_value if v]) == 1:
                    field_value = field_value[0]
            if (acrelation_type, field_value.title()) in relationsSeen:
                continue

            entity = DraftAuthority(
                name = field_value.title(),
                type_controlled = authority_type,
                part_of = instance,
            )
            entity.save()
            draftAuthorities.append(entity)

            relation = DraftACRelation(
                authority = entity,
                type_controlled = acrelation_type,
                part_of = instance,
            )
            draftACRelations.append(relation)
            relationsSeen.add((acrelation_type, field_value.title()))

    return draftAuthorities, draftACRelations


def process_linkeddata(paper, instance):
    linkeddata_fields = [    # Maps LD.type_controlled.name -> Zotero field.
        (DraftCitationLinkedData, [
            ('URI', 'uri'),
            ('DOI', 'doi'),
            ('ISBN', 'isbn'),
            ('ISSN', 'issn'),
        ]),
        (DraftAuthorityLinkedData, [

        ])
    ]

    draftLinkedDataEntries = []

    for model, fields in linkeddata_fields:
        for name, field in fields:
            if hasattr(paper, field):
                linkedDataEntry = model(
                    name = name,
                    value = getattr(paper, field),
                    part_of = instance,
                )
                draftLinkedDataEntries.append(linkedDataEntry)


    return draftLinkedDataEntries


def process_attributes(paper, instance):
    attributeFields = [
        ('PublicationDate', 'date'),
    ]

    attributes = []
    for field, attr in attributeFields:
        if hasattr(paper, attr):
            attribute = DraftAttribute(
                name = field,
                value = getattr(paper, attr),
                part_of = instance,
            )
            attributes.append(attribute)
    return attributes


def _get_citation_by_linkeddata(ident_field, ident_value):
    qs = LinkedData.objects.filter(**{
        'type_controlled__name__icontains': ident_field,
        'universal_resource_name': ident_value
    })
    if qs.count() == 0:
        return

    linkeddata_entry = qs.first()
    return linkeddata_entry.subject


def _draft_linkage(citation, target, relation_type, accession):
    # To maintain consistency in later steps, we will create a
    #  "dummy" DraftCitation based on this production Citation.
    draft_target = DraftCitation.objects.create(**{
        'title': target.title,
        'type_controlled': target.type_controlled,
        'part_of': accession,
    })
    # This DraftCitation is resolved from the start, since we
    #  have already decided what it refers to.
    InstanceResolutionEvent.objects.create(**{
        'for_instance': draft_target,
        'to_instance': target
    })

    return DraftCCRelation.objects.create(**{
        'subject': draft_target,
        'object': citation,
        'type_controlled': relation_type,
        'part_of': accession,
    })


def process_ccrelations(citations, originals, accession):
    """
    Attempt to match up book chapters and book reviews with their respective
    books.
    """

    books = [(c, o) for c, o in zip(citations, originals)
             if c.type_controlled == Citation.BOOK]

    # We assume that ``citations`` and ``originals`` are the same shape, in the
    #  same order.
    for citation, original in zip(citations, originals):
        found = False
        if citation.type_controlled == Citation.CHAPTER:
            if not hasattr(original, 'partof__identifier'):
                continue

            ident_field, ident_value = original.partof__identifier

            for book, original_book in books:
                if getattr(original_book, ident_field) == ident_value:
                    DraftCCRelation.objects.create(**{
                        'subject': book,
                        'object': citation,
                        'type_controlled': DraftCCRelation.INCLUDES_CHAPTER,
                        'part_of': accession,
                    })
                    found = True
                    break

            if not found:   # Look in the production database, via LinkedData.
                production_target = _get_citation_by_linkeddata(ident_field,
                                                                ident_value)
                if production_target is None:
                    continue

                _draft_linkage(citation, production_target,
                               DraftCCRelation.INCLUDES_CHAPTER, accession)

                found = True

        else:
            if hasattr(original, 'review_of'):
                identifiers = getattr(original, 'review_of')
                citation.type_controlled = Citation.REVIEW
                citation.save()

                targets = []
                for identifier in identifiers:
                    if identifier.startswith('CBB'):    # Production citation.
                        try:
                            target = Citation.objects.get(pk=identifier)
                        except Citation.DoesNotExist:
                            print 'Could not find citation with id', identifier
                            continue

                    else:    # ISBN.
                        found = False
                        for book, original_book in books:
                            if getattr(original_book, 'isbn') == identifier:
                                DraftCCRelation.objects.create(**{
                                    'subject': book,
                                    'object': citation,
                                    'type_controlled': DraftCCRelation.REVIEWED_BY,
                                    'part_of': accession,
                                })
                                found = True
                                break
                        if not found:
                            target = _get_citation_by_linkeddata('isbn', identifier)
                            if target is None:
                                continue


                            found = True

                    _draft_linkage(citation, target, DraftCCRelation.REVIEWED_BY,
                                   accession)


def process_paper(paper, instance):
    modelFields = [
        ('title', 'title'),
        ('abstract', 'abstract'),
        ('publication_date', 'date'),
        ('type_controlled', 'documentType'),
        ('page_start', 'pageStart'),
        ('page_end', 'pageEnd'),
        ('pages_free_text', 'pagesFreeText'),
        ('volume', 'volume'),
        ('issue', 'issue'),
    ]
    draftCitation = DraftCitation(part_of = instance)

    for field, attr in modelFields:
        if hasattr(paper, attr):
            setattr(draftCitation, field, getattr(paper, attr))
    draftCitation.save()

    # Build DraftAuthority and DraftACRelation.
    authorities, acrelations = process_authorities(paper, instance)
    for acrelation in acrelations:
        acrelation.citation = draftCitation
        acrelation.save()

    # Linked Data for both the Citation and Authorities.
    linkedData = process_linkeddata(paper, instance)
    for ldEntry in linkedData:
        if type(ldEntry) is DraftCitationLinkedData:
            ldEntry.citation = draftCitation
            ldEntry.save()
        elif type(ldEntry) is DraftAuthorityLinkedData:
            for authority in authorities:
                if authority.type_controlled == 'SE':
                    ldEntry.authority = authority
                    ldEntry.save()

    # Build DraftAttributes.
    attributes = process_attributes(paper, instance)
    for attribute in attributes:
        attribute.citation = draftCitation
        attribute.save()

    draftCitation.save()
    return draftCitation, paper


def process(papers, instance):
    """

    """

    citations, papers = zip(*[process_paper(paper, instance) for paper in papers])
    process_ccrelations(citations, papers, instance)
    return citations
