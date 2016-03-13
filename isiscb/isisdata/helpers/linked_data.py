from rdflib import Graph, URIRef, BNode, Literal
from rdflib.namespace import RDF, FOAF, DC, Namespace, SKOS, DCTERMS, RDFS, OWL
import urllib

isisns = Namespace('http://data.isiscb.org/vocab#')
isisns_props = Namespace('http://data.isiscb.org/properties#')
dbpedia = Namespace('http://dbpedia.org/ontology/')


def generate_rdf(authority):
    g = Graph()

    auth = URIRef("http://data.isiscb.org/authority/" + authority.id) #urllib.quote(authority.name.replace(" ", "_")))

    type = get_type(authority.type_controlled)
    if not type:
        return ''
    g.add( (auth, RDF.type, type) )
    g.add( (auth, RDFS.label, Literal(authority.name)) )

    for attr in authority.attributes.all():
        attr_pred = get_property(attr.type_controlled.name)
        if attr_pred:
            g.add( (auth, attr_pred, Literal(attr.value_freeform)))

    return g.serialize(format='application/rdf+xml')

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
