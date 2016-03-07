from rdflib import Graph, URIRef, BNode, Literal
from rdflib.namespace import RDF, FOAF, DC
import urllib

def generate_rdf(authority):
    g = Graph()

    auth = URIRef("http://data.isiscb.org/isis/" + authority.id) #urllib.quote(authority.name.replace(" ", "_")))

    type = get_type(authority.type_controlled)
    if not type:
        return ''
    g.add( (auth, RDF.type, type) )
    return g.serialize(format='application/rdf+xml')

def get_type(authority_type):
    type_dict = {}
    type_dict['PE'] = FOAF.Person
    type_dict['IN'] = FOAF.Institution
    type_dict['TI'] = DC.PeriodOfTime
    type_dict['GE'] = DC.Coverage
    type_dict['SE'] = None
    type_dict['CT'] = None
    type_dict['CO'] = None
    type_dict['CW'] = None
    type_dict['EV'] = None
    type_dict['CR'] = None
    type_dict['PU'] = None

    return type_dict.get(authority_type, None)
