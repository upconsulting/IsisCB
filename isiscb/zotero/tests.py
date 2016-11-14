from unittest import TestCase
from django.test.client import RequestFactory
from django.contrib.contenttypes.models import ContentType
from django.db import models

import rdflib, datetime, tempfile, types, os
from collections import Counter


from zotero.models import *
from suggest import *
from tasks import *
from zotero.parse import ZoteroIngest
from zotero import ingest

from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.namespace import DC, FOAF, DCTERMS

BIB = Namespace('http://purl.org/net/biblio#')
RSS = Namespace('http://purl.org/rss/1.0/modules/link/')
ZOTERO = Namespace('http://www.zotero.org/namespaces/export#')


# Create your tests here.
datapath = 'zotero/test_data/IsisCBTest.rdf'

AUTHOR = rdflib.URIRef("http://purl.org/net/biblio#authors")

partdetails_fields = [
    ('page_start', 'page_begin'),
    ('page_end', 'page_end'),
    ('pages_free_text', 'pages_free_text'),
    ('issue', 'issue_free_text'),
    ('volume', 'volume_free_text'),
]


class TestPages(TestCase):
    """
    Sometimes we get unicode oddities in the page numbers.
    """

    def test_page_number(self):
        """
        Both of these journal articles should have clear start and end pages.

        """
        book_data = 'zotero/test_data/Journal test.rdf'
        papers = ZoteroIngest(book_data)
        instance = ImportAccession.objects.create(name='TestAccession')
        citations = ingest.IngestManager(papers, instance).process()

        for citation in citations:
            self.assertTrue(citation.page_start is not None)
            self.assertTrue(citation.page_end is not None)

    def tearDown(self):
        Citation.objects.all().delete()
        Authority.objects.all().delete()
        CCRelation.objects.all().delete()
        ACRelation.objects.all().delete()
        InstanceResolutionEvent.objects.all().delete()
        ImportAccession.objects.all().delete()
        DraftAuthority.objects.all().delete()
        DraftCitation.objects.all().delete()
        DraftACRelation.objects.all().delete()
        DraftCCRelation.objects.all().delete()


class TestPublisher(TestCase):
    """
    Information about publisher should be retained.
    """

    def test_publisher_info(self):
        """
        Both of the books in this document have publishers, so we should expect
        corresponding ACRelations.
        """
        book_data = 'zotero/test_data/Book test.rdf'
        papers = ZoteroIngest(book_data)
        instance = ImportAccession.objects.create(name='TestAccession')
        citations = ingest.IngestManager(papers, instance).process()

        for citation in citations:
            type_counts = Counter()
            for rel in citation.authority_relations.all():
                type_counts[rel.type_controlled] += 1
            self.assertEqual(type_counts[DraftACRelation.PUBLISHER], 1)

    def tearDown(self):
        Citation.objects.all().delete()
        Authority.objects.all().delete()
        CCRelation.objects.all().delete()
        ACRelation.objects.all().delete()
        InstanceResolutionEvent.objects.all().delete()
        ImportAccession.objects.all().delete()
        DraftAuthority.objects.all().delete()
        DraftCitation.objects.all().delete()
        DraftACRelation.objects.all().delete()
        DraftCCRelation.objects.all().delete()


class TestExtent(TestCase):
    """
    z:numPages should be interpreted as DraftCitation.extent.
    """

    def test_parse_extent(self):
        """
        Both of the books in this document should have ``extent`` data.
        """
        book_data = 'zotero/test_data/Book test.rdf'
        papers = ZoteroIngest(book_data)
        instance = ImportAccession.objects.create(name='TestAccession')
        citations = ingest.IngestManager(papers, instance).process()

        for citation in citations:
            self.assertGreater(citation.extent, 0)

    def tearDown(self):
        Citation.objects.all().delete()
        Authority.objects.all().delete()
        CCRelation.objects.all().delete()
        ACRelation.objects.all().delete()
        InstanceResolutionEvent.objects.all().delete()
        ImportAccession.objects.all().delete()
        DraftAuthority.objects.all().delete()
        DraftCitation.objects.all().delete()
        DraftACRelation.objects.all().delete()
        DraftCCRelation.objects.all().delete()




class TestBookSeries(TestCase):
    """
    """
    def setUp(self):
        codes = [
            '=151-360=',
            '=102-375=',
            '=150-340=',
            '=102-350=',
            '=103-340=',
            '=160-370=',
            '=160-375=',
            '=151-375=',
            '=121-320=',
            '=120-370=',
            '=123-360=',
            '=160-360=',
            '=161-360=',
            '=150=',
            '=160-380=',
            '=1-330=',
            '=150-370=',
            '=1-340=',
            '=131=',
            '=150-380=',
            '=42-370=',
            '=151-360=',
            '=152-360=',
            '=151-360=',
            '=160=',
            '=150-230=',
            '=160-370=',
            '=150-350=',
            '=163-370=',
            '=140-360=',
            ]

        for code in codes:
            Authority.objects.create(
                name='The real %s' % code,
                type_controlled=DraftAuthority.CONCEPT,
                classification_code=code.replace('=', ''),
            )

    def test_process_bookseries(self):
        """
        If we ingest a citation that is part of something else, we should use
        BOOK_SERIES for the ACRelation.

        We're also double-checking that percent-encoded subject codes are
        resolved correctly.
        """
        book_data = 'zotero/test_data/Books test 1 SR 2016.09.27.rdf'
        papers = ZoteroIngest(book_data)
        instance = ImportAccession.objects.create(name='TestAccession')
        citations = ingest.IngestManager(papers, instance).process()

        self.assertGreater(len(citations), 0)
        for citation in citations:
            citation.refresh_from_db()
            type_counts = Counter()
            for rel in citation.authority_relations.all():
                type_counts[rel.type_controlled] += 1
                if rel.type_controlled == DraftACRelation.SUBJECT:
                    # We have matched all percent-encoded subject authorities.
                    self.assertFalse(rel.authority.name.startswith('='))
            if citation.book_series is not None:
                self.assertEqual(type_counts[DraftACRelation.BOOK_SERIES], 1)

    def tearDown(self):
        Citation.objects.all().delete()
        Authority.objects.all().delete()
        CCRelation.objects.all().delete()
        ACRelation.objects.all().delete()
        InstanceResolutionEvent.objects.all().delete()
        ImportAccession.objects.all().delete()
        DraftAuthority.objects.all().delete()
        DraftCitation.objects.all().delete()
        DraftACRelation.objects.all().delete()
        DraftCCRelation.objects.all().delete()


class TestLanguageParsing(TestCase):
    def test_parse_language(self):
        """
        ISISCB-749 Should parse Language from Zotero metadata.

        All of the chapters in this dataset have language fields.
        """
        book_data = 'zotero/test_data/Chapter Test 8-9-16.rdf'
        for entry in ZoteroIngest(book_data):
            if entry.get('type_controlled')[0].lower() == 'booksection':
                self.assertIn('language', entry)

    def test_process_language(self):
        """
        ISISCB-749 IngestManager should use language data to attempt to fill
        :prop:`.DraftCitation.language`\.
        """
        accession = ImportAccession.objects.create(name=u'test')
        draftcitation = DraftCitation.objects.create(
            title = 'Test',
            type_controlled = DraftCitation.ARTICLE,
            part_of = accession,
        )
        language = Language.objects.create(id='TL', name='TestLanguage')
        data = {
            'language': ['TL'],
        }
        ingest.IngestManager.generate_language_relations(data, draftcitation)
        draftcitation.refresh_from_db()
        self.assertEqual(draftcitation.language, language,
                         "Should match language by ID.")

        data = {
            'language': ['TestLanguage'],
        }
        ingest.IngestManager.generate_language_relations(data, draftcitation)
        draftcitation.refresh_from_db()
        self.assertEqual(draftcitation.language, language,
                         "Otherwise, should match language by ID.")

    def test_accession_language(self):
        """
        :prop:`.DraftCitation.language` should be used to fill
        :class:`.Citation.language`\.
        """
        accession = ImportAccession.objects.create(name=u'test')
        draftcitation = DraftCitation.objects.create(
            title = 'Test',
            type_controlled = DraftCitation.ARTICLE,
            part_of = accession,
        )
        language = Language.objects.create(id='TL', name='TestLanguage')
        rf = RequestFactory()
        request = rf.get('/hello/')
        user = User.objects.create(username='bob', password='what', email='asdf@asdf.com')
        request.user = user

        data = {
            'language': ['TL'],
        }
        ingest.IngestManager.generate_language_relations(data, draftcitation)
        draftcitation.refresh_from_db()
        new_citation = ingest_citation(request, accession, draftcitation)
        self.assertEqual(new_citation.language.first(), language)

    def tearDown(self):
        for model in [DraftCitation, DraftAuthority, DraftACRelation,
                      DraftCCRelation, ImportAccession, DraftCitationLinkedData,
                      DraftAuthorityLinkedData, Authority, AttributeType,
                      User, Attribute, Language]:
            model.objects.all().delete()


class TestBookReviews(TestCase):
    """
    Reviews are linked to book citations via the "reviewed author" field in
    Zotero. The foaf:surname of the target "author" can contain either an

    """
    def setUp(self):
        isbn_type, _ = LinkedDataType.objects.get_or_create(name='ISBN')
        identifiers = [u'CBB001552823', u'CBB001202302', u'CBB001510022',
                       u'CBB001422653', u'CBB001551200']
        isbns = [u'9782853672665', u'9782021111293', u'9783319121017',
                 u'CBB001552823', u'CBB001202302', u'9789004225534',
                 u'CBB001510022', u'CBB001422653', u'CBB001551200',
                 u'9783515104418', u'9788387992842']

        for identifier in identifiers:
            test_book = Citation.objects.create(title='A Test Citation',
                                                type_controlled=Citation.BOOK,
                                                id=identifier)
        for isbn in isbns:
            test_book = Citation.objects.create(title='A Test Citation',
                                                type_controlled=Citation.BOOK)

            LinkedData.objects.create(universal_resource_name=isbn,
                                      type_controlled=isbn_type,
                                      subject=test_book)


    def test_process_bookreviews(self):

        book_data = 'zotero/test_data/IsisReviewExamples.rdf'
        papers = ZoteroIngest(book_data)
        instance = ImportAccession.objects.create(name='TestAccession')
        citations = ingest.IngestManager(papers, instance).process()

        # There is one book in this dataset, and the chapters are chapter of
        #  this book.

        type_counts = Counter()
        for citation in citations:
            type_counts[citation.type_controlled] += 1
            if citation.type_controlled == Citation.REVIEW:
                self.assertGreater(citation.relations_to.count(), 0)
                relation = citation.relations_to.first()
                self.assertEqual(relation.type_controlled,
                                 CCRelation.REVIEWED_BY)

        self.assertEqual(type_counts[Citation.REVIEW], 8)

    def test_ingest_reviews(self):
        rf = RequestFactory()
        request = rf.get('/hello/')
        user = User.objects.create(username='bob', password='what', email='asdf@asdf.com')
        request.user = user

        accession = ImportAccession.objects.create(name='TestAccession')
        book_data = 'zotero/test_data/IsisReviewExamples.rdf'

        for citation in ingest.process(ZoteroIngest(book_data), accession):
            new_citation = ingest_citation(request, accession, citation)

            # CCRelations are no longer created in tasks.ingest_citation; they
            #  are now handled by tasks.ingest_ccrelations, which is called by
            #  tasks.ingest_accession. This is to prevent circular recursion
            #  when attempting to resolve dependencies.
            self.assertEqual(new_citation.relations_to.count(), 0)

    def tearDown(self):
        Citation.objects.all().delete()
        Authority.objects.all().delete()
        ACRelation.objects.all().delete()
        CCRelation.objects.all().delete()
        ImportAccession.objects.all().delete()
        DraftAuthority.objects.all().delete()
        DraftCitation.objects.all().delete()
        DraftACRelation.objects.all().delete()
        DraftCCRelation.objects.all().delete()
        User.objects.all().delete()


class TestBookChapters(TestCase):
    """
    Chapters are linked to book citations via the "Book title" field in Zotero.
    This is represented as dc.isPartOf -> bib:Book.
    """
    def test_process_bookchapters2(self):
        book_data = "zotero/test_data/Chapter Test 8-9-16.rdf"
        papers = ZoteroIngest(book_data)
        instance = ImportAccession.objects.create(name='TestAccession')
        citations = ingest.IngestManager(papers, instance).process()
        type_counts = Counter([c.type_controlled for c in citations])
        self.assertEqual(type_counts[Citation.BOOK], 1)
        self.assertEqual(type_counts[Citation.CHAPTER], 2)
        instance.refresh_from_db()

    def test_process_bookchapters_resolve(self):
        book_data = "zotero/test_data/Chapter Test 8-9-16.rdf"
        papers = ZoteroIngest(book_data)
        accession = ImportAccession.objects.create(name='TestAccession')
        citations = ingest.IngestManager(papers, accession).process()

        accession.refresh_from_db()

        # The ImportAccession should be fully resolved, so we need to create
        #  corresponding Authority records ahead of time.
        for draftauthority in accession.draftauthority_set.all():
            authority = Authority.objects.create(
                name = draftauthority.name,
                type_controlled = draftauthority.type_controlled,
            )
            InstanceResolutionEvent.objects.create(
                for_instance = draftauthority,
                to_instance = authority,
            )
        accession.draftauthority_set.all().update(processed=True)

        #  We need a user for the accession.
        rf = RequestFactory()
        request = rf.get('/hello/')
        user = User.objects.create(username='bob', password='what', email='asdf@asdf.com')
        request.user = user

        prod_citations = ingest_accession(request, accession)
        for citation in prod_citations:
            self.assertGreater(citation.relations_from.count() + citation.relations_to.count(), 0)


    def test_process_bookchapters(self):
        test_book = Citation.objects.create(title='A Test Citation',
                                            type_controlled=Citation.BOOK)
        isbn_type, _ = LinkedDataType.objects.get_or_create(name='ISBN')
        LinkedData.objects.create(universal_resource_name='9783110225784',
                                  type_controlled=isbn_type,
                                  subject=test_book)


        book_data = 'zotero/test_data/BookChapterExamples.rdf'
        papers = ZoteroIngest(book_data)
        instance = ImportAccession.objects.create(name='TestAccession')
        citations = ingest.IngestManager(papers, instance).process()

        # There is one book in this dataset, and the chapters are chapter of
        #  this book.
        book = [c for c in citations if c.type_controlled == Citation.BOOK][0]

        type_counts = Counter()
        for citation in citations:
            type_counts[citation.type_controlled] += 1
            if citation.type_controlled == Citation.CHAPTER:
                self.assertGreater(citation.relations_to.count(), 0)
                relation = citation.relations_to.first()
                self.assertEqual(relation.type_controlled,
                                 CCRelation.INCLUDES_CHAPTER)


        self.assertEqual(type_counts[Citation.BOOK], 2, "There are two unique"
                         "ISBNs, thus two unique books.")
        self.assertEqual(type_counts[Citation.CHAPTER], 6)

    def tearDown(self):
        for model in [DraftCitation, DraftAuthority, DraftACRelation,
                      DraftCCRelation, ImportAccession, DraftCitationLinkedData,
                      DraftAuthorityLinkedData, Authority, AttributeType,
                      Attribute, User, Citation, ACRelation, CCRelation]:
            model.objects.all().delete()


class TestSubjects(TestCase):
    def test_parse_subjects(self):
        papers = ZoteroIngest('zotero/test_data/Hist Europ Idea 2015 41 7.rdf')
        for paper in papers:
            self.assertIn('subjects', paper)

    def test_process_subjects(self):
        Authority.objects.create(name='testauthority', classification_code='140-340')

        papers = ZoteroIngest('zotero/test_data/Hist Europ Idea 2015 41 7.rdf')
        instance = ImportAccession.objects.create(name='TestAccession')
        citations = ingest.IngestManager(papers, instance).process()
        for citation in citations:
            for acrelation in citation.authority_relations.filter(type_controlled=DraftACRelation.CATEGORY):
                if acrelation.authority.name == 'testauthority':
                    self.assertEqual(acrelation.authority.resolutions.count(), 1)

    def tearDown(self):
        Citation.objects.all().delete()
        Authority.objects.all().delete()
        ACRelation.objects.all().delete()
        CCRelation.objects.all().delete()
        ImportAccession.objects.all().delete()
        DraftAuthority.objects.all().delete()
        DraftCitation.objects.all().delete()
        DraftACRelation.objects.all().delete()
        DraftCCRelation.objects.all().delete()
        User.objects.all().delete()



class TestSuggest(TestCase):
    def test_suggest_citation_by_linkeddata(self):
        """
        TODO: complete this.
        """
        accession = ImportAccession(name='test')
        accession.save()

        instance = ImportAccession.objects.create(name='TestAccession')
        citations = ingest.IngestManager(ZoteroIngest(datapath), instance).process()

    def tearDown(self):
        Citation.objects.all().delete()
        Authority.objects.all().delete()
        ACRelation.objects.all().delete()
        CCRelation.objects.all().delete()
        ImportAccession.objects.all().delete()
        DraftAuthority.objects.all().delete()
        DraftCitation.objects.all().delete()
        DraftACRelation.objects.all().delete()
        DraftCCRelation.objects.all().delete()
        User.objects.all().delete()


class TestIngest(TestCase):
    """
    After all :class:`.DraftAuthority` instances have been resolved for a
    :class:`.ImportAccession`\, the curator will elect to ingest all of the
    records in that accession into the production database.
    """

    def setUp(self):
        self.dataset = Dataset.objects.create(name='test dataset')
        self.accession = ImportAccession.objects.create(name='test',
                                                        ingest_to=self.dataset)
        instance = ImportAccession.objects.create(name='TestAccession')

        self.citations = ingest.IngestManager(ZoteroIngest(datapath), self.accession).process()

        # We need a user for the accession.
        rf = RequestFactory()
        self.request = rf.get('/hello/')
        self.user = User.objects.create(username='bob', password='what', email='asdf@asdf.com')
        self.request.user = self.user

        isodate_type = ContentType.objects.get_for_model(ISODateValue)
        self.publicationDateType, _ = AttributeType.objects.get_or_create(
            name='PublicationDate',
            value_content_type=isodate_type,
        )

        # The ImportAccession should be fully resolved, so we need to create
        #  corresponding Authority records ahead of time.
        for draftauthority in self.accession.draftauthority_set.all():
            authority = Authority.objects.create(
                name = draftauthority.name,
                type_controlled = draftauthority.type_controlled,
            )
            InstanceResolutionEvent.objects.create(
                for_instance = draftauthority,
                to_instance = authority,
            )
        self.accession.draftauthority_set.all().update(processed=True)

    def test_ingest_accession(self):
        citation = ingest_accession(self.request, self.accession)
        self.accession.refresh_from_db()

        self.assertEqual(self.accession.citation_set.count(),
                         self.accession.draftcitation_set.count(),
                         'did not ingest all citations')

    def test_ingest_citation(self):
        draftcitation = self.citations[1]
        citation = ingest_citation(self.request, self.accession, draftcitation)

        self.assertIsInstance(citation.created_on, datetime.datetime,
                              'created_on not populated correctly')
        self.assertIsInstance(citation.created_by, User,
                              'created_by not populated correctly')
        if citation.publication_date:
            self.assertIsInstance(citation.publication_date, datetime.date,
                                  'publication_date not populated correctly')
        self.assertFalse(citation.public,
                         'new citation is public; should be non-public')
        self.assertEqual(citation.record_status_value, CuratedMixin.INACTIVE,
                         'new citation is not inactive')
        self.assertEqual(citation.title, draftcitation.title,
                         'title not transferred correctly')
        self.assertEqual(citation.type_controlled,
                         draftcitation.type_controlled,
                         'type_controlled not transferred correctly')
        self.assertTrue(draftcitation.processed,
                        'DraftCitation not flagged as processed')

        self.assertEqual(self.accession.ingest_to, citation.belongs_to,
                         'citation not assigned to the correct dataset')


        model_fields = {f.name: type(f) for f in PartDetails._meta.fields}
        for field, pfield in partdetails_fields:
            draft_value = getattr(draftcitation, field, None)
            if model_fields[pfield] is models.IntegerField:
                try:
                    draft_value = int(draft_value)
                except ValueError:
                    continue

            prod_value = getattr(citation.part_details, pfield, None)
            self.assertEqual(draft_value, prod_value,
                             '%s not populated correctly, %s != %s' % \
                             (pfield, draft_value, prod_value))

        for draft in draftcitation.authority_relations.all():
            self.assertTrue(draft.processed,
                            'DraftACRelation not flagged as processed')
            self.assertEqual(draft.resolutions.count(), 1,
                             'resolution not created for DraftACRelation')

            prod = draft.resolutions.first().to_instance
            self.assertEqual(draft.type_controlled, prod.type_controlled,
                             'type_controlled transferred incorrectly')
            self.assertEqual(draft.authority.name,
                             prod.name_for_display_in_citation,
                             'DraftAuthority name not transferred to ACR')

            self.assertEqual(self.accession.ingest_to, prod.belongs_to)

        attribute = citation.attributes.first()
        self.assertIsInstance(attribute.value_freeform, unicode)
        self.assertEqual(len(attribute.value_freeform), 4,
                         "ISISCB-736: freeform value should be four-digit year")
        self.assertEqual(attribute.type_controlled, self.publicationDateType,
                         'attribute has the wrong type')
        self.assertIsInstance(attribute.value.get_child_class(), ISODateValue,
                              'attribute value instantiates the wrong class')

        self.assertEqual(attribute.value.get_child_class().as_date,
                         citation.publication_date,
                         'publication date attribute incorrect')

    def tearDown(self):
        self.accession.delete()
        self.dataset.delete()
        self.user.delete()

        for model in [DraftCitation, DraftAuthority, DraftACRelation,
                      DraftCCRelation, ImportAccession, DraftCitationLinkedData,
                      DraftAuthorityLinkedData, Authority, AttributeType,
                      Attribute, User, Citation, ACRelation, CCRelation]:
            model.objects.all().delete()


class TestAccessionProperties(TestCase):
    def setUp(self):
        rf = RequestFactory()
        self.request = rf.get('/hello/')
        self.user = User.objects.create(username='bob', password='what', email='asdf@asdf.com')
        self.request.user = self.user

    def test_citations_ready(self):
        accession = ImportAccession.objects.create(name='accession')
        draftauthority = DraftAuthority.objects.create(name='testauthority', part_of=accession)
        draftcitation = DraftCitation.objects.create(title='testcitation', part_of=accession)
        draftcitation2 = DraftCitation.objects.create(title='testcitation2', part_of=accession)
        DraftACRelation.objects.create(authority=draftauthority, citation=draftcitation, type_controlled=DraftACRelation.AUTHOR, part_of=accession)
        DraftCCRelation.objects.create(subject=draftcitation, object=draftcitation2, part_of=accession)

        # draftcitation2 has no ACRelations, so should be ready from the start.
        self.assertEqual(len(accession.citations_ready), 1)

        authority = Authority.objects.create(name='testtest', type_controlled=Authority.PERSON)
        InstanceResolutionEvent.objects.create(for_instance=draftauthority, to_instance=authority)
        draftauthority.processed = True
        draftauthority.save()

        # Now draftcitation is ready, since the target of its one ACRelation is
        #  resolved.
        self.assertEqual(len(accession.citations_ready), 2)

        citations_before = Citation.objects.count()
        ccrelations_before = CCRelation.objects.count()
        ingest_accession(self.request, accession)
        self.assertEqual(citations_before + 2, Citation.objects.count())
        self.assertEqual(ccrelations_before + 1, CCRelation.objects.count())

    def tearDown(self):
        Citation.objects.all().delete()
        Authority.objects.all().delete()
        CCRelation.objects.all().delete()
        ACRelation.objects.all().delete()
        InstanceResolutionEvent.objects.all().delete()
        ImportAccession.objects.all().delete()
        DraftAuthority.objects.all().delete()
        DraftCitation.objects.all().delete()
        DraftACRelation.objects.all().delete()
        DraftCCRelation.objects.all().delete()


class TestZoteroIngesterRDFOnlyReviews(TestCase):
    def test_parse_zotero_rdf(self):
        from pprint import pprint
        ingester = ZoteroIngest("zotero/test_data/Chapter Test 8-9-16.rdf")

        # for datum in ingester:
        #     pprint(datum)



class TestImportMethods(TestCase):
    def test_get_dtype(self):
        """
        :func:`zotero.ingest.IngestManager._get_dtype` is a private function that
        extracts field-data  for :prop`.DraftCitation.type_controlled` from a
        parsed entry.
        """
        for dtype, value in ingest.DOCUMENT_TYPES.iteritems():
            entry = {
                'type_controlled': [dtype],
            }
            data = ingest.IngestManager._get_dtype(entry)
            self.assertIn('type_controlled', data)
            self.assertEqual(data.get('type_controlled'), value)

        data = ingest.IngestManager._get_dtype({})
        self.assertEqual(data.get('type_controlled'), DraftCitation.ARTICLE,
                         "type_controlled should default to Article.")

    def test_get_pages_data(self):
        """
        :func:`zotero.ingest.IngestManager._get_pages_data` is a private function that
        extracts field-data  for for ``page_start``, ``page_end``, and
        ``pages_free_text`` from a  parsed entry.
        """

        # Both start and end available.
        data = ingest.IngestManager._get_pages_data({'pages':[('1', '2')]})
        self.assertEqual(data.get('page_start'), '1')
        self.assertEqual(data.get('page_end'), '2')
        self.assertEqual(data.get('pages_free_text'), u'1-2')

        # Single value available.
        data = ingest.IngestManager._get_pages_data({'pages':[u'555']})
        self.assertEqual(data.get('page_start'), u'555')
        self.assertEqual(data.get('page_end'), None)
        self.assertEqual(data.get('pages_free_text'), u'555')

        # Single value available.
        data = ingest.IngestManager._get_pages_data({'pages':[(u'555',)]})
        self.assertEqual(data.get('page_start'), u'555')
        self.assertEqual(data.get('page_end'), None)
        self.assertEqual(data.get('pages_free_text'), u'555')

    def test_generate_generic_acrelationss(self):
        accession = ImportAccession.objects.create(name=u'test')
        draftcitation = DraftCitation.objects.create(
            title = 'Test',
            type_controlled = DraftCitation.ARTICLE,
            part_of = accession,
        )
        data = {
            u'authors': [{
                u'name_first': u'Fokko Jan',
                u'name': u'Fokko Jan Dijksterhuis',
                u'name_last': u'Dijksterhuis'
            },{
                u'name_first': u'Carsten',
                u'name': u'Carsten Timmermann',
                u'name_last': u'Timmermann'
            }]
        }

        results = ingest.IngestManager.generate_generic_acrelations(
            data, 'authors', draftcitation, DraftAuthority.PERSON,
            DraftACRelation.AUTHOR)
        self.assertEqual(len(results), 2, "Should create two DraftACRelations.")
        self.assertIsInstance(results[0], tuple,
                              "Should return two objects per relation.")
        self.assertIsInstance(results[0][0], DraftAuthority,
                              "The first object is the DraftAuthority"
                              " instance.")
        self.assertIsInstance(results[0][1], DraftACRelation,
                              "The second object is the DraftACRelation"
                              " instance.")
        for draft_authority, draft_relation in results:
            self.assertEqual(draft_relation.citation, draftcitation,
                             "The DraftACRelation should be linked to the"
                             " passed DraftCitation.")
            self.assertEqual(draft_relation.type_controlled,
                             DraftACRelation.AUTHOR,
                             "The DraftACRelation should have the correct"
                             " type.")
            self.assertEqual(draft_authority.type_controlled,
                             DraftAuthority.PERSON,
                             "The DraftAuthority should have the correct type.")

    def test_generate_reviewed_works_relations(self):
        """

        If reviews are found, then ``draft_citation`` will be re-typed as a
        Review.

        Attempts to match reviewed works against (1) citations in this ingest batch,
        (2) citations with matching IDs, and (3) citations with matching linked
        data.
        """
        accession = ImportAccession.objects.create(name=u'test')
        draftcitation = DraftCitation.objects.create(
            title = 'Test',
            type_controlled = DraftCitation.ARTICLE,
            part_of = accession,
        )
        manager = ingest.IngestManager([], accession)
        try:
            r = manager.generate_reviewed_works_relations({}, draftcitation)
        except:
            self.fail("Should not choke on nonsensical data, but rather fail"
                      " quietly.")
        self.assertEqual(draftcitation.type_controlled, DraftCitation.ARTICLE,
                         "If no review is found, type should not be changed.")

        data = {'reviewed_works': [{'name': 'nonsense'}]}

        try:
            r = manager.generate_reviewed_works_relations(data, draftcitation)
        except:
            self.fail("Should not choke on nonsensical data, but rather fail"
                      " quietly.")
        self.assertEqual(len(r), 0,
                         "If the identifier can't be resolved into something"
                         " meaningful, should simply bail.")
        draftcitation.refresh_from_db()


        data = {
            'reviewed_works': [{'name': '12345678'}]
        }
        alt_draftcitation = DraftCitation.objects.create(**{
            'title': 'Alt',
            'type_controlled': DraftCitation.BOOK,
            'part_of': accession,
        })

        manager.draft_citation_map = {'12345678': alt_draftcitation}
        r = manager.generate_reviewed_works_relations(data, draftcitation)
        self.assertEqual(len(r), 1, "If a matching citation is found in this"
                                    " accession, it should be associated.")
        draftcitation.refresh_from_db()
        self.assertEqual(draftcitation.type_controlled, DraftCitation.REVIEW,
                         "If a review is found, type should be review.")

        citation = Citation.objects.create(
            title = 'A real citation',
            type_controlled = Citation.BOOK,
        )
        data = {
            'reviewed_works': [{'name': citation.id}]
        }

        r = manager.generate_reviewed_works_relations(data, draftcitation)
        self.assertEqual(len(r), 1, "If a matching citation is found in the"
                                    " database, it should be associated.")
        self.assertEqual(r[0][0].resolutions.first().to_instance, citation)
        draftcitation.refresh_from_db()
        self.assertEqual(draftcitation.type_controlled, DraftCitation.REVIEW,
                         "If a review is found, type should be review.")

    def test_generate_book_chapter_relations(self):
        accession = ImportAccession.objects.create(name=u'test')
        draftcitation = DraftCitation.objects.create(
            title = 'Test',
            type_controlled = DraftCitation.ARTICLE,
            part_of = accession,
        )
        data = {
            u'part_of': [{
                u'linkeddata': [(u'ISBN', u'9781874267621')],
                u'title': u'Thinking Through the Environment: Green Approaches to Global History',
                u'type_controlled': u'Book'
            }],
        }
        manager = ingest.IngestManager([], accession)
        result = manager.generate_book_chapter_relations(data, draftcitation)

        alt_draftcitation = DraftCitation.objects.create(**{
            'title': u'Thinking Through the Environment: Green Approaches to Global History',
            'type_controlled': DraftCitation.BOOK,
            'part_of': accession,
        })

        manager.draft_citation_map = {'9781874267621': alt_draftcitation}
        r = manager.generate_book_chapter_relations(data, draftcitation)
        self.assertEqual(len(r), 1, "If a matching citation is found in this"
                                    " accession, it should be associated.")
        draftcitation.refresh_from_db()
        self.assertEqual(draftcitation.type_controlled, DraftCitation.CHAPTER,
                         "If a book is found, type should be chapter.")

    def test_generate_part_of_relations(self):
        accession = ImportAccession.objects.create(name=u'test')
        draftcitation = DraftCitation.objects.create(
            title = 'Test',
            type_controlled = DraftCitation.ARTICLE,
            part_of = accession,
        )
        data = {
            'part_of':  [{
                u'linkeddata': [(u'ISSN', u'0191-6599')],
                u'title': u'History of European Ideas',
                u'type_controlled': u'Journal'
            }, {
                u'title': u'En temps & lieux.',
                u'type_controlled': u'Series'
            }],
        }

        result = ingest.IngestManager.generate_part_of_relations(data, draftcitation)
        self.assertEqual(len(result), 2, "Should yield two records")


    def test_generate_citation_linkeddata(self):
        """
        :func:`zotero.ingest.IngestManager.generate_citation_linkeddata` creates new
        :class:`.DraftCitationLinkedData` instances from a parsed entry.
        """
        accession = ImportAccession.objects.create(name=u'test')
        draftcitation = DraftCitation.objects.create(
            title = 'Test',
            type_controlled = DraftCitation.ARTICLE,
            part_of = accession,
        )
        data = {
             u'linkeddata': [
                (u'URI',
                 u'http://www.journals.uchicago.edu/doi/abs/10.1086/687176'),
                (u'ISSN', u'0021-1753'),
             ]
        }
        linkeddata = ingest.IngestManager.generate_citation_linkeddata(data, draftcitation)
        self.assertEqual(len(linkeddata), 2, "Should create two records.")
        for linkeddatum in linkeddata:
            self.assertIsInstance(linkeddatum, DraftCitationLinkedData,
                                  "Should return DraftCitationLinkedData"
                                  " instances.")
            self.assertEqual(linkeddatum.citation, draftcitation,
                             "Should point to the passed DraftCitation.")

        try:
            ingest.IngestManager.generate_citation_linkeddata({}, draftcitation)
        except:
            self.fail("Should not choke when no linkeddata are present.")

    def test_generate_draftcitation(self):
        """
        :func:`zotero.ingest.IngestManager.generate_draftcitation` creates a new
        :class:`.DraftCitation` instance from a parsed entry.
        """
        _title = u'The Test Title'
        _date = datetime.datetime.now()
        _vol = u'5'
        _iss = u'1'
        _abstract = u'A very abstract abstract'
        data = {
            u'title': [_title],
            u'type_controlled': [u'Book'],
            u'publication_date': [_date],
            u'pages': [('373', '374')],
            u'volume': [_vol],
            u'issue': [_iss],
            u'abstract': [_abstract],
        }
        accession = ImportAccession.objects.create(name=u'test')
        manager = ingest.IngestManager([], accession)
        draft_citation = manager.generate_draftcitation(data, accession)
        self.assertIsInstance(draft_citation, DraftCitation,
                              "generate_draftcitation should return a"
                              " DraftCitation instance.")
        self.assertEqual(draft_citation.title, _title)
        self.assertEqual(draft_citation.type_controlled, DraftCitation.BOOK)
        self.assertEqual(draft_citation.volume, _vol)
        self.assertEqual(draft_citation.issue, _iss)
        self.assertEqual(draft_citation.abstract, _abstract)
        self.assertEqual(draft_citation.page_start, '373')
        self.assertEqual(draft_citation.page_end, '374')
        self.assertEqual(draft_citation.pages_free_text, '373-374')

    def test_find_mapped_authority(self):
        """
        :func:`zotero.ingest.IngestManager._find_mapped_authority` attempts to find an
        :class:`.Authority` record using the table in
        ``zotero/AuthorityIDmap.tab``.
        """

        authority = Authority.objects.create(
            name = 'test_authority',
            type_controlled = Authority.PERSON,
            id = 'CBA000113709'
        )
        candidate = ingest.IngestManager._find_mapped_authority('Whoops', '13')
        self.assertEqual(candidate, authority,
                         "Should return the corresponding authority.")

        self.assertEqual(ingest.IngestManager._find_mapped_authority('Whoops', '12'), None,
                         "If not found, should return None.")

    def test_find_encoded_authority(self):
        """
        :func:`zotero.ingest.IngestManager._find_encoded_authority` attempts to find an
        :class:`.Authority` record using an equals-encoded classification code.
        """

        authority = Authority.objects.create(
            name = 'test_authority',
            type_controlled = Authority.PERSON,
            id = 'CBA000113709',
            classification_code='55-56'
        )
        authority2 = Authority.objects.create(
            name = 'test_authority2',
            type_controlled = Authority.PERSON,
            id = 'CBA000113710',
            classification_code='6'
        )
        candidate = ingest.IngestManager._find_encoded_authority('=56-55=', None)
        self.assertEqual(candidate, authority,
                         "Should return the corresponding authority.")

        candidate = ingest.IngestManager._find_encoded_authority('=6=', None)
        self.assertEqual(candidate, authority2,
                         "Should return the corresponding authority.")

        self.assertEqual(ingest.IngestManager._find_encoded_authority('=55-56=', None), None,
                         "If not found, should return None.")
    def test_find_explicit_authority(self):
        """
        :func:`zotero.ingest.IngestManager._find_explicit_authority` attempts to find an
        existing :class:`.Authority` using an explicit identifier.
        """
        authority = Authority.objects.create(
            name = 'test_authority',
            type_controlled = Authority.PERSON,
            id = 'CBA000113709',
            classification_code='55-56'
        )
        candidate = ingest.IngestManager._find_explicit_authority('CBA000113709', None)
        self.assertEqual(candidate, authority,
                         "Should return the corresponding authority when"
                         " the identifier is passed as the label.")

        candidate = ingest.IngestManager._find_explicit_authority(None, 'CBA000113709')
        self.assertEqual(candidate, authority,
                         "Should return the corresponding authority when"
                         " the identifier is passed as the identifier.")

        candidate = ingest.IngestManager._find_explicit_authority(None, ' CBA000113709')
        self.assertEqual(candidate, authority,
                         "Should be tolerant of whitespace.")

    def test_generate_subject_acrelations(self):
        accession = ImportAccession.objects.create(name=u'test')
        draftcitation = DraftCitation.objects.create(
            title = 'Test',
            type_controlled = DraftCitation.ARTICLE,
            part_of = accession,
        )

        data = {
            u'subjects': [
                (u'National Socialism', u'1145'),
                (u'1938', None),
                (u'T\xf6nnies, Ferdinand', u'CBA000102771'),
                (u'=370-140=', None)
            ],
        }

        nat_soc = Authority.objects.create(name='National Socialism', id='CBA000114074', type_controlled=Authority.CONCEPT)
        ferdinand = Authority.objects.create(name=u'T\xf6nnies, Ferdinand', id='CBA000102771', type_controlled=Authority.PERSON)
        something = Authority.objects.create(name='Something', classification_code='140-370', type_controlled=Authority.PERSON)

        results = ingest.IngestManager.generate_subject_acrelations(data, draftcitation)
        self.assertEqual(len(results), 4, "Should return four results")
        for da, dac in results:
            if da.name != '1938':
                self.assertEqual(da.resolutions.count(), 1)

    def test_check_for_authority_reference(self):
        data = {
            u'subjects': [
                (u'moral philosophy', u'CBA000120197'),
                (u'Science and civilization', u'1122'),
                (u'Enlightenment', u'416'),
                (u'Montesquieu, Charles de Secondat, Baron de (1689-1755)',
                u'11244'),
                (u'18th century', u'12'),
                (u'Diderot, Denis (1713-1784)', u'8290'),
                (u'Raynal, Guillaume (1713-1796)', u'12117'),
                (u'Colonialism', u'246'),
                (u'=6=', None)
            ],
        }

    def test_source_data_is_preserved(self):
        book_data = 'zotero/test_data/Book test.rdf'
        papers = ZoteroIngest(book_data)
        instance = ImportAccession.objects.create(name='TestAccession')
        citations = ingest.IngestManager(papers, instance).process()
        for citation in citations:
            self.assertNotEqual(citation.source_data, 'null')

    def tearDown(self):
        for model in [DraftCitation, DraftAuthority, DraftACRelation,
                      DraftCCRelation, ImportAccession, DraftCitationLinkedData,
                      DraftAuthorityLinkedData, Authority, AttributeType,
                      Attribute]:
            model.objects.all().delete()


class TestExtraDataParsing(TestCase):
    """
    Curators may want to pass additional data in Zotero records, beyond what
    is supported by the Zotero scheme. To do this, they may insert key/value
    pairs in curly braces in certain fields.
    """

    def test_find_extra_data(self):
        """
        :meth:`.IngestManager.find_extra_data` parses strings for explicit
        key/value data in curly braces, and returns the data as a list.
        """

        raw = 'Some freeform text {key:value}'
        data = ingest.IngestManager.find_extra_data(raw)
        self.assertIsInstance(data, list)
        self.assertIn('key', dict(data))
        self.assertEqual(dict(data).get('key'), 'value')

    def test_apply_extra_data(self):
        """
        :meth:`.IngestManager.apply_extra_data` handles parsed key/value pairs
        and returns a callable that will update a model instance accordingly.
        The callable should return the instance that was passed.
        """

        class DummyObject(object):
            pass

        raw = 'Some freeform text {name:The Best Name}'
        data = ingest.IngestManager.find_extra_data(raw)
        func = ingest.IngestManager.apply_extra_data(data)

        obj = func(DummyObject())
        self.assertEqual(obj.name, "The Best Name")


    def test_match_extra_viaf(self):
        """
        :meth:`.IngestManager.apply_extra_data` should operate on VIAF IDs.
        """

        raw = 'Some freeform text {viaf:76382712}'
        data = ingest.IngestManager.find_extra_data(raw)
        func = ingest.IngestManager.apply_extra_data(data)

        obj = DraftAuthority.objects.create(
            name = 'Pratchett, Terry, 1948-2015',
            type_controlled = DraftAuthority.PERSON,
            part_of = ImportAccession.objects.create(name='TestAccession')
        )

        obj = func(obj)
        self.assertEqual(obj.linkeddata.count(), 1)
        self.assertEqual(obj.linkeddata.first().value, 'http://viaf.org/viaf/76382712')

    def test_match_is_applied_during_ingest(self):
        """
        When creating :class:`.DraftACRelation`\s during ingest, authority
        names are parsed for VIAF IDs.
        """
        accession = ImportAccession.objects.create(name='Test')
        draftcitation = DraftCitation.objects.create(
            title = 'Test',
            type_controlled = DraftCitation.ARTICLE,
            part_of = accession,
        )


        data = {
            u'authors': [{
                u'name_first': u'Fokko Jan',
                u'name': u'Fokko Jan Dijksterhuis {viaf:76382712}',
                u'name_last': u'Dijksterhuis'
            },{
                u'name_first': u'Carsten',
                u'name': u'Carsten Timmermann {viaf:76382713}',
                u'name_last': u'Timmermann'
            }]
        }

        results = ingest.IngestManager.generate_generic_acrelations(
            data, 'authors', draftcitation, DraftAuthority.PERSON,
            DraftACRelation.AUTHOR)
        draftcitation.refresh_from_db()
        for relation in draftcitation.authority_relations.all():
            self.assertEqual(relation.authority.linkeddata.count(), 1)

    def test_viaf_data_survives_to_production(self):
        """
        When accessioned from Zotero to IsisData, linkeddata for authorities
        persist.
        """
        accession = ImportAccession.objects.create(name='Test')
        draftcitation = DraftCitation.objects.create(
            title = 'Test',
            type_controlled = DraftCitation.ARTICLE,
            part_of = accession,
        )
        data = {
            u'authors': [{
                u'name_first': u'Fokko Jan',
                u'name': u'Fokko Jan Dijksterhuis {viaf:76382712}',
                u'name_last': u'Dijksterhuis'
            },{
                u'name_first': u'Carsten',
                u'name': u'Carsten Timmermann {viaf:76382713}',
                u'name_last': u'Timmermann'
            }]
        }
        ingest.IngestManager.generate_generic_acrelations(
            data, 'authors', draftcitation, DraftAuthority.PERSON,
            DraftACRelation.AUTHOR)
        draftcitation.refresh_from_db()
        for relation in draftcitation.authority_relations.all():
            auth = Authority.objects.create(name=relation.authority.name, type_controlled=relation.authority.type_controlled)
            ingest.IngestManager.resolve(relation.authority, auth)

        rf = RequestFactory()
        request = rf.get('/hello/')
        user = User.objects.create(username='bob', password='what', email='asdf@asdf.com')
        request.user = user

        new_citation = ingest_citation(request, accession, draftcitation)

        for relation in new_citation.acrelation_set.all():
            self.assertEqual(relation.authority.linkeddata_entries.count(), 1)

    def tearDown(self):
        for model in [DraftCitation, DraftAuthority, DraftACRelation,
                      DraftCCRelation, ImportAccession, DraftCitationLinkedData,
                      DraftAuthorityLinkedData, Authority, AttributeType,
                      User, Attribute]:
            model.objects.all().delete()
