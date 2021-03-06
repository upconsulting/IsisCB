from __future__ import absolute_import
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from rdflib import Graph, URIRef, BNode, Literal
from rdflib.namespace import RDF, FOAF, DC, Namespace, SKOS, DCTERMS, RDFS, OWL, NamespaceManager
import urllib.request, urllib.parse, urllib.error
from isisdata.templatetags.app_filters import *
from .mods_helper import *

isisns = Namespace('http://data.isiscb.org/vocab#')
isisns_props = Namespace('http://data.isiscb.org/properties#')
dbpedia = Namespace('http://dbpedia.org/ontology/')
madsrdf = Namespace('http://www.loc.gov/mads/rdf/v1#')
modsrdf = Namespace("http://www.loc.gov/mods/rdf/v1#")
relators = Namespace("http://id.loc.gov/vocabulary/relators/")
identifiers = Namespace('http://id.loc.gov/vocabulary/identifiers/')


def generate_authority_rdf(authority):
    g = Graph()

    auth = URIRef("http://data.isiscb.org/authority/" + authority.id) #urllib.quote(authority.name.replace(" ", "_")))

    type = get_auth_type(authority.type_controlled)
    if not type:
        return ''
    g.add( (auth, RDF.type, type) )
    g.add( (auth, RDF.type, madsrdf.Authority) )
    g.add( (auth, RDFS.label, Literal(authority.name)) )
    g.add( (auth, madsrdf.authoritativeLabel, Literal(authority.name)) )

    for attr in authority.attributes.all():
        attr_pred = get_property(attr.type_controlled.name)
        if attr_pred:
            g.add( (auth, attr_pred, Literal(attr.value_freeform)))

    nsMgr = NamespaceManager(g)
    nsMgr.bind('madsrdf', madsrdf)
    nsMgr.bind('isiscb', isisns)
    nsMgr.bind('isisvocab', isisns_props)
    return g.serialize(format='application/rdf+xml')

def generate_citation_rdf(citation):
    graph = Graph()

    citation_uri = URIRef("http://data.isiscb.org/authority/" + citation.id)
    graph.add( (citation_uri, RDF.type, modsrdf.ModsResource) )

    # add title, author, date, and type
    add_general_info(graph, citation, citation_uri)

    # add Abstract
    abstract =  citation.human_readable_abstract
    graph.add( (citation_uri, modsrdf.abstract, Literal(abstract)) )

    # start/end Pages
    start_page = citation.part_details.page_begin
    end_page = citation.part_details.page_end

    # add part info (volume, page number, etc)
    # there should only be one?
    periodicals = citation.acrelation_set.filter(type_controlled__in=['PE', 'BS'])
    for periodical in periodicals:
        host_BNode = BNode()
        graph.add( (citation_uri, modsrdf.relatedHost, host_BNode) )

        # title of jounral
        host_title_BNode = BNode()
        graph.add( (host_BNode, modsrdf.titlePrincipal, host_title_BNode) )
        graph.add( (host_title_BNode, RDF.type, madsrdf.Title))
        graph.add( (host_title_BNode, RDFS.label, Literal(bleach_safe(periodical.authority.name))) )

        # can we assume that there will always be a periodical/book series when there are page numbers?
        if not end_page:
            end_page = start_page

        # create part node for pages, volumes, etc.
        part_volume_BNode = BNode()
        graph.add( (host_BNode, modsrdf.part, part_volume_BNode) )

        if start_page:
            graph.add( (part_volume_BNode, modsrdf.partStart, Literal(start_page)) )

        if end_page:
            graph.add( (part_volume_BNode, modsrdf.partEnd, Literal(end_page)) )


        # add volume
        volume = get_volume(citation)
        if volume:
            # add volume
            graph.add( (part_volume_BNode, RDF.type, modsrdf.Part) )
            graph.add( (part_volume_BNode, modsrdf.partDetailType, Literal("volume")) )
            graph.add( (part_volume_BNode, modsrdf.partNumber, Literal(volume)) )

        # add issue
        # TODO: this is very confusing. do we have 2 part entries here?
        issue = get_issue(citation)
        if issue:
            # create part node to add issue nr
            part_BNode = BNode()
            graph.add( (host_BNode, modsrdf.part, part_BNode) )
            graph.add( (part_BNode, RDF.type, modsrdf.Part) )

            graph.add( (part_BNode, modsrdf.partDetailType, Literal("issue")) )
            graph.add( (part_BNode, modsrdf.partNumber, Literal(issue)) )

    # add publishers (apparently schools/institutions are publishers as well?)
    publishers = get_publisher(citation)
    for pub in publishers:
        graph.add( (citation_uri, modsrdf.publisher, Literal(pub.authority.name)) )

    # add included in
    included_in = CCRelation.objects.filter(object_id=citation.id, type_controlled='IC', object__public=True)
    for included in included_in:
        host_included_BNode = BNode()
        graph.add( (citation_uri, modsrdf.relatedHost, host_included_BNode) )

        add_general_info(graph, included.subject, host_included_BNode)

        # can we assume that there is either a periodical or book series?
        if not end_page:
            end_page = start_page

        part_book_BNode = BNode()
        graph.add( (host_included_BNode, modsrdf.part, part_book_BNode) )


        if start_page:
            graph.add( (part_book_BNode, modsrdf.partStart, Literal(start_page)) )

        if end_page:
            graph.add( (part_book_BNode, modsrdf.partEnd, Literal(end_page)) )

    add_linked_data_links(graph, citation, citation_uri)

    # bind namespace prefixes
    nsMgr = NamespaceManager(graph)
    nsMgr.bind('identifier', identifiers)
    nsMgr.bind('madsrdf', madsrdf)
    nsMgr.bind('modsrdf', modsrdf)
    nsMgr.bind('relators', relators)
    # pretty-xml would be nice, but seems to be buggy
    return graph.serialize(format='xml') #pretty-xml, turtle') #

def add_general_info(graph, citation, citation_node):
    title_BNode = BNode()
    graph.add( (citation_node, modsrdf.titlePrincipal, title_BNode) )
    graph.add( (title_BNode, RDF.type, madsrdf.Title))
    graph.add( (title_BNode, RDFS.label, Literal(bleach_safe(get_title(citation)))) )

    # add authors and contributors
    authors = citation.get_all_contributors
    first = True
    for author in authors:
        author_BNode = BNode()

        # only the first author should be principalName, so after the first
        # we set this to false
        if first:
            graph.add( (citation_node, modsrdf.principalName, author_BNode) )
            first = False
        else:
            graph.add( (citation_node, modsrdf.name, author_BNode) )
        graph.add( (citation_node, get_relator(author.type_controlled), author_BNode) )

        graph.add( (author_BNode, RDF.type, madsrdf.Name) )
        graph.add( (author_BNode, RDFS.label, Literal(author.authority.name)) )

    # publication Date
    date = get_pub_year(citation)
    graph.add( (citation_node, modsrdf.dateCreated, Literal(date)) )

    # add genre
    citation_type = get_type(citation.type_controlled)
    genre_BNode = BNode()
    graph.add( (citation_node, modsrdf.genre, genre_BNode) )
    graph.add( (genre_BNode, RDFS.label, Literal(citation_type)) )
    graph.add( (genre_BNode, RDF.type, madsrdf.GenreForm) )

def add_linked_data_links(graph, citation, citation_node):
    for linked_data in citation.linkeddata_entries.all():
        graph.add( (citation_node, get_linked_data_type(linked_data.type_controlled.name) , Literal(linked_data.universal_resource_name)) )

def get_linked_data_type(name):
    ld_type_dict = {}
    ld_type_dict['DOI'] = identifiers.doi
    ld_type_dict['ISBN'] = identifiers.isbn

    return ld_type_dict[name]

def get_relator(type_controlled):
    type_dict = {}
    type_dict['AU'] = relators.aut
    type_dict['CO'] = relators.ctb
    type_dict['ED'] = relators.edt
    type_dict['AD'] = relators.ths
    type_dict['TR'] = relators.trl

    return type_dict[type_controlled]

def get_property(authority_attr):
    attr_dict = {}
    # the ontology should specify that BirthToDeathDates is of type owl:FunctionalProperty,
    # rdf:Property, and owl:DatatypeProperty
    attr_dict['BirthToDeathDates'] = isisns_props.BirthToDeathDates
    attr_dict['Birth date'] = dbpedia.BirthDate
    attr_dict['FlourishedDates'] = dbpedia.activeYears

    return attr_dict[authority_attr]

def get_auth_type(authority_type):
    mesh = Namespace('http://id.nlm.nih.gov/mesh/vocab#')
    dcmitype = Namespace('http://purl.org/dc/dcmitype/')

    type_dict = {}
    type_dict['PE'] = FOAF.Person
    type_dict['IN'] = FOAF.Institution
    type_dict['TI'] = DC.PeriodOfTime
    type_dict['GE'] = DC.Coverage
    type_dict['SE'] = FOAF.Document
    type_dict['CT'] = isisns.ClassificationTerm
    type_dict['CO'] = SKOS.Concept
    type_dict['CW'] = FOAF.Document
    type_dict['EV'] = dcmitype.Event
    type_dict['CR'] = isisns.CrossReference
    type_dict['PU'] = dbpedia.Publisher

    return type_dict.get(authority_type, None)
