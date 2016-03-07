from rdflib import Graph, URIRef, BNode, Literal
from rdflib.namespace import RDF, FOAF, DC, Namespace
import urllib

def generate_rdf(authority):
    g = Graph()

    auth = URIRef("http://data.isiscb.org/authority/" + authority.id) #urllib.quote(authority.name.replace(" ", "_")))

    type = get_type(authority.type_controlled)
    if not type:
        return ''
    g.add( (auth, RDF.type, type) )
    return g.serialize(format='application/rdf+xml')

def get_type(authority_type):
    mesh = Namespace('http://id.nlm.nih.gov/mesh/vocab#')
    isisns = Namespace('http://data.isiscb.org/vocab#')

    type_dict = {}
    type_dict['PE'] = FOAF.Person
    type_dict['IN'] = FOAF.Institution
    type_dict['TI'] = DC.PeriodOfTime
    type_dict['GE'] = DC.Coverage
    type_dict['SE'] = mesh.PublicationType
    type_dict['CT'] = isisns.ClassificationTerm
    type_dict['CO'] = isisns.Concept
    type_dict['CW'] = None
    type_dict['EV'] = None
    type_dict['CR'] = None
    type_dict['PU'] = None

    return type_dict.get(authority_type, None)
