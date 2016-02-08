import os
import re
import xml.etree.ElementTree as ET
import iso8601
import rdflib

import codecs
import chardet
import unicodedata

import logging

from datetime import datetime

from models import *

# rdflib complains a lot.
logging.getLogger("rdflib").setLevel(logging.ERROR)

# RDF terms.
RDF = u'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
DC = u'http://purl.org/dc/elements/1.1/'
FOAF = u'http://xmlns.com/foaf/0.1/'
PRISM = u'http://prismstandard.org/namespaces/1.2/basic/'
RSS = u'http://purl.org/rss/1.0/modules/link/'

URI_ELEM = rdflib.URIRef("http://purl.org/dc/terms/URI")
TYPE_ELEM = rdflib.term.URIRef(RDF + u'type')
VALUE_ELEM = rdflib.URIRef(RDF + u'value')
LINK_ELEM = rdflib.URIRef(RSS + u"link")
FORENAME_ELEM = rdflib.URIRef(FOAF + u'givenname')
SURNAME_ELEM = rdflib.URIRef(FOAF + u'surname')
VOL = rdflib.term.URIRef(PRISM + u'volume')
IDENT = rdflib.URIRef(DC + u"identifier")
TITLE = rdflib.term.URIRef(DC + u'title')


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
                    value.append(data)
                elif value not in [None, '']:
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
        'isPartOf': 'journal'
    }

    meta_elements = [
        ('date', rdflib.URIRef("http://purl.org/dc/elements/1.1/date")),
        ('identifier',
         rdflib.URIRef("http://purl.org/dc/elements/1.1/identifier")),
        ('abstract', rdflib.URIRef("http://purl.org/dc/terms/abstract")),
        ('authors_full', rdflib.URIRef("http://purl.org/net/biblio#authors")),
        ('seriesEditors', rdflib.URIRef("http://www.zotero.org/namespaces/export#seriesEditors")),
        ('editors', rdflib.URIRef("http://purl.org/net/biblio#editors")),
        ('contributors', rdflib.URIRef("http://purl.org/net/biblio#contributors")),
        ('translators', rdflib.URIRef("http://www.zotero.org/namespaces/export#translators")),
        ('link', rdflib.URIRef("http://purl.org/rss/1.0/modules/link/link")),
        ('title', rdflib.URIRef("http://purl.org/dc/elements/1.1/title")),
        ('isPartOf', rdflib.URIRef("http://purl.org/dc/terms/isPartOf")),
        ('pages', rdflib.URIRef("http://purl.org/net/biblio#pages")),
        ('documentType',
         rdflib.URIRef("http://www.zotero.org/namespaces/export#itemType"))]

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

    def handle_identifier(self, value):
        """

        """

        identifier = unicode(self.graph.value(subject=value, predicate=VALUE_ELEM))
        ident_type = self.graph.value(subject=value, predicate=TYPE_ELEM)
        if ident_type == URI_ELEM:
            self.set_value('uri', identifier)


    def handle_link(self, value):
        """
        rdf:link rdf:resource points to the resource described by a record.
        """
        for s, p, o in self.graph.triples((value, None, None)):
            if p == LINK_ELEM:
                return unicode(o).replace('file://', '')

    def handle_date(self, value):
        """
        Attempt to coerced date to ISO8601.
        """
        try:
            return iso8601.parse_date(unicode(value))
        except iso8601.ParseError:
            for datefmt in ("%B %d, %Y", "%Y-%m", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    # TODO: remove str coercion.
                    return datetime.strptime(unicode(value), datefmt).date()
                except ValueError:
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
        return [a for a in authors if a is not None]

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
            forename = ''

        try:
            surname = norm([e[2] for e in surname_iter][0])
        except IndexError:
            surname = ''

        if surname == '' and forename == '':
            return
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
            elif p == TITLE:
                journal = unicode(o)    # Journal title.
        return journal

    def handle_pages(self, value):
        return tuple(value.split('-'))

    def postprocess_pages(self, entry):
        if len(entry.pages) == 1:
            start = entry.pages
            end = None
        else:
            start, end = entry.pages
        setattr(entry, 'pageStart', start)
        setattr(entry, 'pageEnd', end)
        del entry.pages

    def postprocess_link(self, entry):
        """
        Attempt to load full-text content from resource.
        """

        if not self.follow_links:
            return

        if type(entry.link) is not list:
            entry.link = [entry.link]

        for link in list(entry.link):
            if not os.path.exists(link):
                continue

            mime_type = magic.from_file(link, mime=True)
            if mime_type == 'application/pdf':
                structuredfeature = extract_pdf(link)
            elif mime_type == 'text/plain':
                structuredfeature = extract_text(link)
            else:
                structuredfeature = None

            if not structuredfeature:
                continue

            fset_name = mime_type.split('/')[-1] + '_text'
            if not fset_name in self.full_text:
                self.full_text[fset_name] = {}

            if hasattr(self, 'index_by'):
                ident = getattr(entry, self.index_by)
            else:   # If `index_by` is not set, use `uri` by default.
                ident = entry.uri

            self.full_text[fset_name][ident] = structuredfeature


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
        A list of :class:`.Paper`\s.
    """

    parser = ZoteroParser(path, follow_links=False)
    papers = parser.parse()

    return papers


def process_authorities(paper):
    authority_fields = [
        ('PE', 'AU', 'authors_full'),
        ('PE', 'ED', 'editors'),
        ('PE', 'ED', 'seriesEditors'),
        ('PE', 'CO', 'contributors'),
        ('PE', 'TR', 'translators'),
        ('SE', 'PE', 'journal'),
    ]

    draftAuthorities = []
    draftACRelations = []
    for authority_type, acrelation_type, field in authority_fields:
        if not hasattr(paper, field):
            continue

        field_value = getattr(paper, field)
        # TODO: make this more DRY.
        if type(field_value) is list and authority_type == 'PE':
            for last, first in field_value:
                entity = DraftAuthority(
                    name = ('%s %s' % (first, last)).title(),
                    name_last = last.title(),
                    name_first = first.title(),
                    type_controlled = authority_type,
                )
                entity.save()
                draftAuthorities.append(entity)

                relation = DraftACRelation(
                    authority = entity,
                    type_controlled = acrelation_type,
                )
                draftACRelations.append(relation)
        else:
            entity = DraftAuthority(
                name = field_value.title(),
                type_controlled = authority_type,
            )
            entity.save()
            draftAuthorities.append(entity)

            relation = DraftACRelation(
                authority = entity,
                type_controlled = acrelation_type,
            )
            draftACRelations.append(relation)

    return draftAuthorities, draftACRelations


def process_paper(paper):

    modelFields = [
        ('title', 'title'),
        ('abstract', 'abstract'),
        ('publication_date', 'date'),
        ('type_controlled', 'documentType'),
        ('page_start', 'pageStart'),
        ('page_end', 'pageEnd'),
        ('volume', 'volume'),
        ('issue', 'issue'),
    ]
    draftCitation = DraftCitation()

    for field, attr in modelFields:
        if hasattr(paper, attr):
            setattr(draftCitation, field, getattr(paper, attr))
    draftCitation.save()

    authorities, acrelations = process_authorities(paper)
    for acrelation in acrelations:
        acrelation.citation = draftCitation
        acrelation.save()

    # acrelations = process_acrelations(paper, authors, 'AU')

    draftCitation.save()
    return draftCitation


def process(papers):
    """

    """

    return [process_paper(paper) for paper in papers]
