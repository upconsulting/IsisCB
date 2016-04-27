from django.test import TestCase
import rdflib
import datetime

from parser import *
from models import *
from suggest import *


# Create your tests here.
datapath = 'zotero/test_data/IsisCBTest.rdf'

AUTHOR = rdflib.URIRef("http://purl.org/net/biblio#authors")


# class TestParse(TestCase):
#     def test_parse(self):
#         """
#         There should not be a Paper for every relevant entry in the RDF.
#         """
#         papers = read(datapath)
#
#         graph = rdflib.Graph()
#         graph.parse(datapath)
#         expected = 0
#         for element in ZoteroParser.entry_elements:
#             query = 'SELECT * WHERE { ?p a %s }' % element
#             expected += len([r[0] for r in graph.query(query)])
#
#         self.assertNotEqual(len(papers), expected)
#
#     def test_parse_authors(self):
#         """
#         There should be a unique author for each unique author in the RDF.
#         """
#         papers = read(datapath)
#
#
#         parsed_authors = set([])    # Unique authors.
#         parsed_authorships = 0      # Paper-Author associations.
#         for paper in papers:
#             parsed_authorships += len(paper.authors_full)
#             for author in paper.authors_full:
#                 parsed_authors.add(author)
#
#         graph = rdflib.Graph()
#         graph.parse(datapath)
#         expected_authors = set([])    # Unique authors.
#         expected_authorships = 0      # Paper-Author associations.
#         for s, p, o in graph.triples((None, AUTHOR, None)):
#             expected_authors.add(o)
#             expected_authorships += 1
#
#         self.assertEqual(len(parsed_authors), len(expected_authors))
#         self.assertEqual(parsed_authorships, expected_authorships)
#
#     def test_parse_titles(self):
#         """
#         Each entry should have a title.
#         """
#         papers = read(datapath)
#         for paper in papers:
#             self.assertGreater(len(paper.title), 0)
#
#     def test_parse_dates(self):
#         """
#         Each entry should have a date.
#         """
#         papers = read(datapath)
#         for paper in papers:
#             self.assertTrue(hasattr(paper, 'date'))
#
#     def test_parse_types(self):
#         papers = read(datapath)
#         for paper in papers:
#             self.assertTrue(hasattr(paper, 'documentType'))
#             self.assertEqual(len(paper.documentType), 2)
#             self.assertIn(paper.documentType, ZoteroParser.document_types.values())
#
#
# class TestIngest(TestCase):
#     def setUp(self):
#         self.instance = ImportAccession.objects.create(name='TestAccession')
#
#     def test_process_paper(self):
#         papers = read(datapath)
#         for paper in papers:
#             draftCitation = process_paper(paper, self.instance)
#             self.assertIsInstance(draftCitation, DraftCitation)
#
#     def test_handle_authorities(self):
#         papers = read(datapath)
#
#         for paper in papers:
#             authorities, acrelations = process_authorities(paper, self.instance)
#             self.assertGreater(len(authorities), 0)
#             self.assertGreater(len(acrelations), 0)
#
#     def test_handle_linkeddata(self):
#         papers = read(datapath)
#         for paper in papers:
#             ldentries = process_linkeddata(paper, self.instance)
#
#     def test_process(self):
#         papers = read(datapath)
#         citations = process(papers, self.instance)
#
#         self.assertGreater(len(citations), 0)
#         self.assertIsInstance(citations[0], DraftCitation)
#
#
# class TestSuggest(TestCase):
#     def test_suggest_citation_by_linkeddata(self):
#         accession = ImportAccession(name='test')
#         accession.save()
#         papers = read(datapath)
#         citations = process(papers, accession)
#
#         print suggest_by_linkeddata(citations[0])
