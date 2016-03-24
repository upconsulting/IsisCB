from rdflib import Graph, URIRef, BNode, Literal
from rdflib.namespace import RDF, FOAF, DC, Namespace, SKOS, DCTERMS, RDFS, OWL, NamespaceManager
import urllib
from isisdata.templatetags.app_filters import *

isisns = Namespace('http://data.isiscb.org/vocab#')
isisns_props = Namespace('http://data.isiscb.org/properties#')
dbpedia = Namespace('http://dbpedia.org/ontology/')
madsrdf = Namespace('http://www.loc.gov/mads/rdf/v1#')
modsrdf = Namespace("http://www.loc.gov/mods/rdf/v1#")
relators = Namespace("http://id.loc.gov/vocabulary/relators/")


def generate_authority_rdf(authority):
    g = Graph()

    auth = URIRef("http://data.isiscb.org/authority/" + authority.id) #urllib.quote(authority.name.replace(" ", "_")))

    type = get_type(authority.type_controlled)
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
    g = Graph()

    citation_uri = URIRef("http://data.isiscb.org/authority/" + citation.id)
    g.add( (citation_uri, RDF.type, modsrdf.ModsResource) )

    titleBNode = BNode()
    g.add( (citation_uri, modsrdf.titlePrincipal, titleBNode) )
    g.add( (titleBNode, RDF.type, madsrdf.Title))
    g.add( (titleBNode, RDFS.label, Literal(bleach_safe(get_title(citation)))) )

    # add authors and contributors
    authors = citation.get_all_contributors
    first = True
    for author in authors:
        authorBNode = BNode()

        # only the first author should be principalName, so after the first
        # we set this to false
        if first:
            g.add( (citation_uri, modsrdf.principalName, authorBNode) )
            first = False
        else:
            g.add( (citation_uri, modsrdf.name, authorBNode) )
        g.add( (authorBNode, RDF.type, madsrdf.Name) )
        g.add( (authorBNode, RDFS.label, Literal(author.authority.name)) )

        g.add( (citation_uri, get_relator(author.type_controlled), authorBNode) )


    # bind namespace prefixes
    nsMgr = NamespaceManager(g)
    nsMgr.bind('madsrdf', madsrdf)
    nsMgr.bind('modsrdf', modsrdf)
    nsMgr.bind('relators', relators)
    return g.serialize(format='pretty-xml')

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

def get_type(authority_type):
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
