from __future__ import absolute_import
from __future__ import unicode_literals


from builtins import next
from builtins import map
from builtins import str
from builtins import object
import os, re, rdflib, zipfile, tempfile, codecs, chardet, unicodedata, iso8601
import shutil, copy, logging
import xml.etree.ElementTree as ET

from django.conf import settings

from datetime import datetime
from unidecode import unidecode

import re, itertools
# rdflib complains a lot.
logging.getLogger("rdflib").setLevel(logging.ERROR)

from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.namespace import DC, FOAF, DCTERMS, split_uri

BIB = Namespace('http://purl.org/net/biblio#')
RSS = Namespace('http://purl.org/rss/1.0/modules/link/')
ZOTERO = Namespace('http://www.zotero.org/namespaces/export#')
PRISM = Namespace('http://prismstandard.org/namespaces/1.2/basic/')
VCARD = Namespace('http://nwalsh.com/rdf/vCard#')

RESOURCE_CLASSES = [
    BIB.Illustration, BIB.Recording, BIB.Legislation, BIB.Document,
    BIB.BookSection, BIB.Book, BIB.Data, BIB.Letter, BIB.Report,
    BIB.Article, BIB.Thesis, BIB.Manuscript, BIB.Image,
    BIB.ConferenceProceedings,
]


FIELD_NAMES = dict([
    (DC.title, u'title'),
    (DCTERMS.alternative, u'title'),
    (DCTERMS.abstract, u'abstract'),
    (DC.date, u'publication_date'),
    (RDF.type, u'type_controlled'),
    (ZOTERO.itemType, u'type_controlled'),
    (ZOTERO.numPages, u'extent'),
    (PRISM.volume, u'volume'),
    (PRISM.number, u'issue'),
    (DCTERMS.dateSubmitted, u'date_submitted'),
    (DC.identifier, u'linkeddata'),
    (DC.description, u'extra'),

    (BIB.authors, u'authors'),
    (ZOTERO.seriesEditors, u'series_editors'),
    (BIB.editors, u'editors'),
    (BIB.contributors, u'contributors'),
    (ZOTERO.translators, u'translators'),

    (RSS.link, u'source'),
    (DCTERMS.isPartOf, u'part_of'),
    (BIB.pages, u'pages'),
    (RSS.type, u'content_type'),
    (DC.subject, u'subjects'),
    (DCTERMS.subject, u'subjects'),
    (ZOTERO.reviewedAuthors, u'reviewed_works'),
    (DC.publisher, u'publisher'),
    (ZOTERO.language, 'language'),
])


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


class EntryWrapper(object):
    """
    Convenience wrapper for entries in :class:`.ZoteroIngest`\.
    """
    def __init__(self, entry):
        self.entry = entry

    def get(self, key, default=None):
        return self.entry.get(key, default)

    def __getitem__(self, key):
        return self.entry[key]

    def __setitem__(self, key, value):
        self.entry[key] = value


class ZoteroIngest(object):
    """
    Ingest Zotero RDF and attachments contained in a zip archive.

    Parameters
    ----------
    path : str
        Location of ZIP archive containing Zotero RDF and attachments.
    """
    handlers = [
        (DC.date, u'date'),
        (DCTERMS.dateSubmitted, u'date'),
        (DC.identifier, u'identifier'),
        (DCTERMS.abstract, u'abstract'),
        (BIB.authors, u'name'),
        (ZOTERO.seriesEditors, u'name'),
        (BIB.editors, u'name'),
        (BIB.contributors, u'name'),
        (ZOTERO.translators, u'name'),
        (RSS.link, u'link'),
        (DC.title, u'title'),
        (DCTERMS.isPartOf, u'isPartOf'),
        (BIB.pages, u'pages'),
        (RDF.type, u'document_type'),
        (RSS.type, u'content_type'),
        (DC.subject, u'subjects'),
        (DCTERMS.subject, u'subjects'),
        (ZOTERO.reviewedAuthors, u'name'),
        (DC.publisher, u'publisher'),
        (ZOTERO.numPages, u'extent'),
    ]

    def __init__(self, path, classes=copy.deepcopy(RESOURCE_CLASSES)):
        self.file_paths = {}
        if path.endswith('.zip'):
            self._unpack_zipfile(path)
        else:
            self.rdf = path
            self.zipfile = None

        self._correct_zotero_violation()
        self._init_graph(self.rdf, classes=classes)
        self.data = []    # All results will go here.


    def _unpack_zipfile(self, path):
        """
        Extract all files in the zipfile at ``path`` into a temporary directory.
        """
        self.zipfile = zipfile.ZipFile(path)
        self._init_dtemp()

        self.paths = []
        for file_path in self.zipfile.namelist():

            if path.startswith('.'):
                continue
            temp_path = self.zipfile.extract(file_path, self.dtemp)
            if temp_path.endswith('.rdf'):
                self.rdf = temp_path
            else:
                self.file_paths[file_path] = temp_path

    def _correct_zotero_violation(self):
        """
        Zotero produces invalid RDF, so we need to directly intervene before
        parsing the RDF document.
        """
        with open(self.rdf, 'r') as f:
            corrected = f.read().replace('rdf:resource rdf:resource',
                                         'link:link rdf:resource')
        with open(self.rdf, 'w') as f:
            f.write(corrected)

    def _init_graph(self, rdf_path, classes=RESOURCE_CLASSES):
        """
        Load the RDF document as a :class:`rdflib.Graph`\.
        """
        self.graph = rdflib.Graph()
        self.graph.parse(rdf_path)
        self.entries = []

        self.classes = copy.deepcopy(classes)
        self.current_class = None
        self.current_entries = None

    def _init_dtemp(self):
        self.dtemp = tempfile.mkdtemp()

    def _get_resources_nodes(self, resource_class):
        """
        Retrieve all nodes in the graph with type ``resource_class``.

        Parameters
        ----------
        resource_class : :class:`rdflib.URIRef`

        Returns
        -------
        generator
            Yields nodes.
        """
        return self.graph.subjects(RDF.type, resource_class)

    def _new_entry(self):
        """
        Start work on a new entry in the dataset.
        """
        self.data.append({})

    def _set_value(self, predicate, new_value):
        """
        Assign ``new_value`` to key ``predicate`` in the current entry.

        For the sake of consistency, each predicate in the entry corresponds to
        a list of values, even if only one value is present.
        """
        if not predicate:
            return

        try:
            current_value = self.current.get(predicate, [])
        except IndexError:
            raise RuntimeError("_new_entry() must be called before values"
                               " can be set.")
        if isinstance(new_value, list):
            current_value += new_value
        else:
            current_value.append(new_value)
        self.current[predicate] = current_value

    def _get_handler(self, predicate):
        """
        Retrieve the handler defined for ``predicate``, if there is one.
        Otherwise, returns a callable that coerces any passed arguments to
        native Python types.

        Parameters
        ----------
        predicate : :class:`rdflib.URIRef` or str

        Returns
        -------
        instancemethod or lambda
            Callable that accepts a pair of positional arguments (presumed to
            be predicate and value) and returns a (predicate, value) tuple.
        """
        predicate = dict(self.handlers).get(predicate, predicate)
        handler_name = 'handle_{predicate}'.format(predicate=predicate)

        # If there is no defined handler, we minimally want to end up with
        #  native Python types. Returning a callable here avoids extra code.
        generic = lambda *args: list(map(self._to_python, args))
        return getattr(self, handler_name, generic)

    def _to_python(self, obj):
        """
        Ensure that any :class:`rdflib.URIRef` instances are coerced to a
        native Python type.
        """
        return obj.toPython() if hasattr(obj, 'toPython') else obj

    def _relabel_predicate(self, predicate):
        if type(predicate) is str:
            predicate = URIRef(predicate)
        return FIELD_NAMES.get(predicate, split_uri(predicate)[1])

    def handle(self, predicate, value):
        """
        Farm out any defined processing logic for a predicate/value pair.

        Parameters
        ----------
        predicate : :class:`rdflib.URIRef` or str
        value : :class:`.URIRef` or :class:`.BNode` or :class:`.Literal`

        Returns
        -------
        tuple
            Predicate, value.
        """
        predicate, value = self._get_handler(predicate)(predicate, value)
        if predicate:
            predicate = self._relabel_predicate(predicate)
        # predicate = self._to_python(predicate)
        return predicate, self._to_python(value)

    def handle_document_type(self, predicate, node):
        if type(node) is URIRef:
            node = self._relabel_predicate(node)
        return predicate, node

    def handle_pages(self, predicate, node):
        value = node.toPython()
        if type(value) is str:
            value = unidecode(value)
        return predicate, tuple(value.split('-'))

    def handle_publisher(self, predicate, node):
        """
        Publisher is usually a BNode.
        """
        for s, p, o in self.graph.triples((node, None, None)):
            if p == FOAF.name:
                return predicate, o.toPython()
        return predicate, None

    def handle_extent(self, predicate, node):
        value = node.toPython()
        try:
            value = float(value)
        except ValueError:    # Not numeric.
            return predicate, str(value)

        if type(value) is float:
            value = round(value)
        try:
            return predicate, int(value)
        except ValueError:
            return predicate, 0

    def handle_isPartOf(self, predicate, node):
        """
        Unpack DCTERMS.isPartOf relations, to extract journals names, books,
        etc.

        Parameters
        ----------
        predicate : :class:`rdflib.URIRef` or str
        value : :class:`.URIRef` or :class:`.BNode` or :class:`.Literal`

        Returns
        -------
        tuple

        """
        parent_document = []
        # this is a nested object and needs to be marked as such
        for p, o in self.graph.predicate_objects(node):
            if p == DC.identifier:
                # Zotero (in all of its madness) makes some identifiers, like
                #  DOIs, properties of Journals rather than the Articles to
                #  which they belong. The predicate for these relations
                #  is identifier, and the object contains both the identifier
                #  type and the identifier itself, eg.
                #       "DOI 10.1017/S0039484"
                try:
                    name, ident_value = tuple(str(o).split(' '))
                    if name.upper() in ['ISSN', 'ISBN']:
                        if name.upper() == 'ISBN':
                            ident_value = ident_value.replace('-', '')
                        parent_document.append((self._relabel_predicate(p), [(name.upper(), ident_value)]))
                    elif name.upper() == 'DOI':
                        self._set_value(*self.handle(p, o))
                except ValueError:
                    pass
            elif p in [DC.title, DCTERMS.alternative, RDF.type]:
                if p == RDF.type:
                    o = self._relabel_predicate(o)
                parent_document.append(self.handle(p, o))
            elif p == PRISM.volume:
                self._set_value('volume', self._to_python(o))
            elif p == PRISM.number:
                self._set_value('issue', self._to_python(o))
        return predicate, dict(parent_document)

    def handle_subjects(self, predicate, node):
        # IEXP-24: somtimes/potentially always, the subject node contains an
        # anonymous node that will display its idea if we don't traverse further
        # e.g
        # <dc:subject>
        #   <z:AutomaticTag><rdf:value>Australia</rdf:value></z:AutomaticTag>
        # </dc:subject>
        if type(node) == BNode:
            node = self.graph.value(subject=node, predicate=RDF.value)
        match = re.match('([^\[]+)\[([A-Z0-9\w]+)\]', node.toPython())
        if match:
            name, identifier = match.groups()
            return predicate, (name.strip(), identifier.strip())
        else:
            return predicate, (node.toPython(), None)

    def handle_identifier(self, predicate, node):
        """
        Parse an ``DC.identifier`` node.

        If the identifier is an URI, we pull this out an assign it with a
        non-URI predicate; this will directly populate the ``Resource.uri``
        field in the database.

        Parameters
        ----------
        predicate : :class:`rdflib.URIRef`
        node : :class:`rdflib.BNode`

        Returns
        -------
        tuple
            Predicate and value.
        """

        identifier = self.graph.value(subject=node, predicate=RDF.value)
        ident_type = self.graph.value(subject=node, predicate=RDF.type)
        # if ident_type == DCTERMS.URI:
        #     return 'uri', identifier

        # Some identifiers are compound objects, with explicit types and values.
        if ident_type and identifier:
            if type(ident_type) is URIRef:
                ident_type = self._relabel_predicate(ident_type)
            return predicate, (ident_type, self._to_python(identifier))

        # Others simply encode the type and value in the target node itself.
        else:
            try:
                name, ident_value = tuple(str(node).split(' '))
                name = name.upper()
                if name in ['ISSN', 'ISBN']:
                    if name == 'ISBN':
                        ident_value = ident_value.replace('-', '')
                return predicate, (name, ident_value)
            except ValueError:
                pass
        return None, None

    def handle_link(self, predicate, node):
        """
        rdf:link rdf:resource points to the resource described by a record.

        Parameters
        ----------
        predicate : :class:`rdflib.URIRef`
        node : :class:`rdflib.BNode`

        Returns
        -------
        tuple
            Predicate and value.
        """
        link_data = []
        for p, o in self.graph.predicate_objects(node):
            if p == DC.identifier:
                p, o = self.handle_identifier(p, o)
            elif p == RSS.link:
                link_path =  self._to_python(o).replace('file://', '')
                p, o = 'link', self.file_paths.get(link_path, link_path)
            else:
                p, o = self.handle(p, o)
            if type(p) is URIRef:
                p = self._relabel_predicate(p)
            link_data.append((p, self._to_python(o)))
        return predicate, dict(link_data)

    def handle_date(self, predicate, node):
        """
        Attempt to coerce date to ISO8601.
        """
        node = node.toPython()
        try:
            return predicate, iso8601.parse_date(node)
        except iso8601.ParseError:
            for datefmt in ("%B %d, %Y", "%Y-%m", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    # TODO: remove str coercion.
                    return predicate, datetime.strptime(node, datefmt).date()
                except ValueError:
                    return predicate, node

    def handle_name(self, predicate, node):
        """
        Extract a concise surname, forename tuple from a composite person.

        Parameters
        ----------
        predicate : :class:`rdflib.URIRef`
        node : :class:`rdflib.BNode`

        Returns
        -------
        tuple
            Predicate and value.
        """
        norm = lambda s: s.toPython()
        author_data = []
        for s, p, o in self.graph.triples((node, None, None)):
            if isinstance(o, BNode):
                # IEXP-139: apparently sometimes the node is called givenName not givenname,
                # hence this uglyness here
                forename_iter1 = self.graph.objects(o, FOAF.givenname)
                forename_iter2 = self.graph.objects(o, FOAF.givenName)
                surname_iter = self.graph.objects(o, FOAF.surname)
                forename = u' '.join(map(norm, [n for n in itertools.chain(forename_iter1, forename_iter2)]))
                surname = u' '.join(map(norm, [n for n in surname_iter]))
                data = {
                    u'name': ' '.join([forename, surname]).strip(),
                    u'name_last': surname,
                    u'name_first': forename,
                    u'list_position': str(p),
                }
                if surname.startswith('http://'):
                    data.update({'uri': surname,})
                author_data.append(data)

        # sort authors by position in list and set data display order
        author_data = sorted(author_data, key=lambda author: author[u'list_position'])
        def set_idx(author):
            lst_pos = author[u'list_position'][author[u'list_position'].rfind("_")+1:]
            author[u'data_display_order'] = lst_pos
        list(map(set_idx, author_data))

        return predicate, author_data

    def process(self, entry):
        """
        Process all predicate/value pairs for a single ``entry``
        :class:`rdflib.BNode` representing a resource.
        """

        if entry is None:
            raise RuntimeError('entry must be a specific node')

        # figure out if entry is a nested entry (e.g. book referenced by book chapter)
        # since subjects returns a generator we have to attempt to iterate over it
        for subject in self.graph.subjects(DCTERMS.isPartOf, entry):
            self._set_value("role", "fallback")
            break
        
        list([self._set_value(*self.handle(*p_o)) for p_o in self.graph.predicate_objects(entry)])

    def __iter__(self):
        return self

    def __next__(self):
        next_entry = None
        while next_entry is None:
            try:
                next_entry = next(self.current_entries)
            except (StopIteration, AttributeError, TypeError):
                try:
                    self.current_class = self.classes.pop()
                except IndexError:    # Out of classes.
                    raise StopIteration()
                self.current_entries = self._get_resources_nodes(self.current_class)

        self._new_entry()
        self.process(next_entry)
        return self.current.entry

    @property
    def current(self):
        return EntryWrapper(self.data[-1])

    def __len__(self):
        return sum([len(list(self._get_resources_nodes(cl))) for cl in self.classes])

    def __del__(self):
        """
        Remove temporary files.
        """
        if hasattr(self, 'dtemp'):
            shutil.rmtree(self.dtemp)
