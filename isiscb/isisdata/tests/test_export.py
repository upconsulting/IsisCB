import unittest, mock
from isisdata import export    # Ha!
from isisdata.models import *


class TestExportCSV(unittest.TestCase):
    def test_output(self):
        for i in xrange(5):
            Citation.objects.create(title='Citation %i' % i, type_controlled=Citation.ARTICLE)
        columns = [export.object_id, export.citation_title]

        class FakeFile(object):
            def __init__(self):
                self.data = []

            def write(self, data):
                self.data.append(data)

        f = FakeFile()
        qs = Citation.objects.all()
        export.generate_csv(f, qs, columns)
        self.assertEqual(len(f.data), qs.count() + 1,
                         "Should generate one line per object, plus a header.")

        def tearDown(self):
            Citation.objects.all().delete()
            Authority.objects.all().delete()
            ACRelation.objects.all().delete()


class TestColumn(unittest.TestCase):
    """
    :class:`.export.Column` should provide a uniform interface for data-prep
    functions.
    """

    def test_column_calls_fnx(self):
        """
        Calling a :class:`.Column` should result in a call to the underlying
        function.
        """
        test_fnx = mock.Mock(side_effect=lambda o, e, x: o)
        test_column = export.Column('Test', test_fnx)
        self.assertEqual('foo', test_column('foo', []))
        self.assertEqual(test_fnx.call_count, 1)

    def test_column_enforces_input_expectation(self):
        """
        If a :class:`.Column` is instantiated with a specific input expectation
        (e.g. a model class), that expectation should be enforced when the
        column is called.
        """

        test_fnx = mock.Mock(side_effect=lambda o, e: o + 1)
        test_column = export.Column('Test', test_fnx, int)
        with self.assertRaises(AssertionError):
            test_column('Definitely not an int', [])
        self.assertEqual(test_fnx.call_count, 0,
                         "The underlying function should not be called if the"
                         " input expectation is not met.")


class TestCitationAuthorColumn(unittest.TestCase):
    """
    The :func:`.export.citation_author` column retrieves the names of the
    author(s) of a citation.
    """

    def test_citation_has_single_author_with_config(self):
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        author = Authority.objects.create(name='Author', id="AUT1C", type_controlled=Authority.PERSON)
        ACRelation.objects.create(citation=citation, id="ACR1", authority=author, type_controlled=ACRelation.AUTHOR)
        expected = "ACR_ID ACR1 || ACRStatus Active || ACRType Author || ACRDisplayOrder 1.0 || ACRNameForDisplayInCitation  || AuthorityID AUT1C || AuthorityStatus Active || AuthorityType Person || AuthorityName Author"
        self.assertEqual(expected, export.citation_author(citation, [], config={'authority_delimiter': " || "}))

    def test_citation_has_single_author_no_config(self):
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        author = Authority.objects.create(name='Author', id="AUT1", type_controlled=Authority.PERSON)
        ACRelation.objects.create(citation=citation, id="ACR1", authority=author, type_controlled=ACRelation.AUTHOR)
        expected = "ACR_ID ACR1 ACRStatus Active ACRType Author ACRDisplayOrder 1.0 ACRNameForDisplayInCitation  AuthorityID AUT1 AuthorityStatus Active AuthorityType Person AuthorityName Author"
        self.assertEqual(expected, export.citation_author(citation, []))

    def test_citation_has_single_author_with_display_name_with_config(self):
        """
        If the ``name_for_display_in_citation`` field is filled on the
        authorship :class:`.ACRelation`\, its value should be preferred.
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        author = Authority.objects.create(name='Author', id="AUT1C", type_controlled=Authority.PERSON)
        relation = ACRelation.objects.create(citation=citation, id="ACR1", authority=author, type_controlled=ACRelation.AUTHOR, name_for_display_in_citation='Some other name')
        expected = "ACR_ID ACR1 || ACRStatus Active || ACRType Author || ACRDisplayOrder 1.0 || ACRNameForDisplayInCitation Some other name || AuthorityID AUT1C || AuthorityStatus Active || AuthorityType Person || AuthorityName Author"
        self.assertEqual(expected, export.citation_author(citation, [], config={'authority_delimiter': " || "}))

    def test_citation_has_single_author_with_display_name_no_config(self):
        """
        If the ``name_for_display_in_citation`` field is filled on the
        authorship :class:`.ACRelation`\, its value should be preferred.
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        author = Authority.objects.create(name='Author', id="AUT1", type_controlled=Authority.PERSON)
        relation = ACRelation.objects.create(citation=citation, id="ACR1", authority=author, type_controlled=ACRelation.AUTHOR, name_for_display_in_citation='Some other name')
        expected = "ACR_ID ACR1 ACRStatus Active ACRType Author ACRDisplayOrder 1.0 ACRNameForDisplayInCitation Some other name AuthorityID AUT1 AuthorityStatus Active AuthorityType Person AuthorityName Author"
        self.assertEqual(expected, export.citation_author(citation, []))

    def test_citation_has_multiple_authors_with_config(self):
        """
        Multiple authors should be separated by semi-colons.
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        author_one = Authority.objects.create(name='AuthorOne', id="AUT1C", type_controlled=Authority.PERSON)
        author_two = Authority.objects.create(name='AuthorTwo', id="AUT2C", type_controlled=Authority.PERSON)
        ACRelation.objects.create(citation=citation, id="ACR1", authority=author_one, type_controlled=ACRelation.AUTHOR, data_display_order=1)
        ACRelation.objects.create(citation=citation, id="ACR2", authority=author_two, type_controlled=ACRelation.AUTHOR, data_display_order=2)
        expected1 = "ACR_ID ACR1 || ACRStatus Active || ACRType Author || ACRDisplayOrder 1.0 || ACRNameForDisplayInCitation  || AuthorityID AUT1C || AuthorityStatus Active || AuthorityType Person || AuthorityName AuthorOne"
        expected2 = "ACR_ID ACR2 || ACRStatus Active || ACRType Author || ACRDisplayOrder 2.0 || ACRNameForDisplayInCitation  || AuthorityID AUT2C || AuthorityStatus Active || AuthorityType Person || AuthorityName AuthorTwo"
        self.assertEqual(u'%s // %s' % (expected1, expected2), export.citation_author(citation, [], config={'authority_delimiter': " || "}))

    def test_citation_has_multiple_authors_no_config(self):
        """
        Multiple authors should be separated by semi-colons.
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        author_one = Authority.objects.create(name='AuthorOne', id="AUT1", type_controlled=Authority.PERSON)
        author_two = Authority.objects.create(name='AuthorTwo', id="AUT2", type_controlled=Authority.PERSON)
        ACRelation.objects.create(citation=citation, id="ACR1", authority=author_one, type_controlled=ACRelation.AUTHOR, data_display_order=1)
        ACRelation.objects.create(citation=citation, id="ACR2", authority=author_two, type_controlled=ACRelation.AUTHOR, data_display_order=2)
        expected1 = "ACR_ID ACR1 ACRStatus Active ACRType Author ACRDisplayOrder 1.0 ACRNameForDisplayInCitation  AuthorityID AUT1 AuthorityStatus Active AuthorityType Person AuthorityName AuthorOne"
        expected2 = "ACR_ID ACR2 ACRStatus Active ACRType Author ACRDisplayOrder 2.0 ACRNameForDisplayInCitation  AuthorityID AUT2 AuthorityStatus Active AuthorityType Person AuthorityName AuthorTwo"
        self.assertEqual(u'%s // %s' % (expected1, expected2), export.citation_author(citation, []))

    def tearDown(self):
        Citation.objects.all().delete()
        Authority.objects.all().delete()
        ACRelation.objects.all().delete()


class TestCitationEditorColumn(unittest.TestCase):
    """
    The :func:`.export.citation_editor` column retrieves the names of the
    editor(s) of a citation.
    """

    def test_citation_has_single_editor_with_config(self):
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        editor = Authority.objects.create(name='Editor', id="ED1C", type_controlled=Authority.PERSON)
        ACRelation.objects.create(citation=citation, id="ACR1", authority=editor, type_controlled=ACRelation.EDITOR)
        expected = "ACR_ID ACR1 || ACRStatus Active || ACRType Editor || ACRDisplayOrder 1.0 || ACRNameForDisplayInCitation  || AuthorityID ED1C || AuthorityStatus Active || AuthorityType Person || AuthorityName Editor"
        self.assertEqual(expected, export.citation_editor(citation, [], config={'authority_delimiter': " || "}))

    def test_citation_has_single_editor_no_config(self):
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        editor = Authority.objects.create(name='Editor', id="ED1", type_controlled=Authority.PERSON)
        ACRelation.objects.create(citation=citation, id="ACR1", authority=editor, type_controlled=ACRelation.EDITOR)
        expected = "ACR_ID ACR1 ACRStatus Active ACRType Editor ACRDisplayOrder 1.0 ACRNameForDisplayInCitation  AuthorityID ED1 AuthorityStatus Active AuthorityType Person AuthorityName Editor"
        self.assertEqual(expected, export.citation_editor(citation, []))

    def test_citation_has_single_author_with_display_name_with_config(self):
        """
        If the ``name_for_display_in_citation`` field is filled on the
        authorship :class:`.ACRelation`\, its value should be preferred.
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        editor = Authority.objects.create(name='Editor', id="ED1C", type_controlled=Authority.PERSON)
        relation = ACRelation.objects.create(citation=citation, id="ACR1", authority=editor, type_controlled=ACRelation.EDITOR, name_for_display_in_citation='Some other name')
        expected = "ACR_ID ACR1 || ACRStatus Active || ACRType Editor || ACRDisplayOrder 1.0 || ACRNameForDisplayInCitation Some other name || AuthorityID ED1C || AuthorityStatus Active || AuthorityType Person || AuthorityName Editor"
        self.assertEqual(expected, export.citation_editor(citation, [], config={'authority_delimiter': " || "}))

    def test_citation_has_single_author_with_display_name_no_config(self):
        """
        If the ``name_for_display_in_citation`` field is filled on the
        authorship :class:`.ACRelation`\, its value should be preferred.
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        editor = Authority.objects.create(name='Editor', id="ED1", type_controlled=Authority.PERSON)
        relation = ACRelation.objects.create(citation=citation, id="ACR1", authority=editor, type_controlled=ACRelation.EDITOR, name_for_display_in_citation='Some other name')
        expected = "ACR_ID ACR1 ACRStatus Active ACRType Editor ACRDisplayOrder 1.0 ACRNameForDisplayInCitation Some other name AuthorityID ED1 AuthorityStatus Active AuthorityType Person AuthorityName Editor"
        self.assertEqual(expected, export.citation_editor(citation, []))

    def test_citation_has_multiple_authors_with_config(self):
        """
        Multiple editors should be separated by semi-colons.
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        editor_one = Authority.objects.create(name='EditorOne', id="ED1C", type_controlled=Authority.PERSON)
        editor_two = Authority.objects.create(name='EditorTwo', id="ED2C", type_controlled=Authority.PERSON)
        ACRelation.objects.create(citation=citation, id="ACR1", authority=editor_one, type_controlled=ACRelation.EDITOR, data_display_order=1)
        ACRelation.objects.create(citation=citation, id="ACR2", authority=editor_two, type_controlled=ACRelation.EDITOR, data_display_order=2)
        expected1 = "ACR_ID ACR1 || ACRStatus Active || ACRType Editor || ACRDisplayOrder 1.0 || ACRNameForDisplayInCitation  || AuthorityID ED1C || AuthorityStatus Active || AuthorityType Person || AuthorityName EditorOne"
        expected2 = "ACR_ID ACR2 || ACRStatus Active || ACRType Editor || ACRDisplayOrder 2.0 || ACRNameForDisplayInCitation  || AuthorityID ED2C || AuthorityStatus Active || AuthorityType Person || AuthorityName EditorTwo"
        self.assertEqual(u'%s // %s' % (expected1, expected2), export.citation_editor(citation, [], config={'authority_delimiter': " || "}))

    def test_citation_has_multiple_authors_no_config(self):
        """
        Multiple editors should be separated by semi-colons.
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        editor_one = Authority.objects.create(name='EditorOne', id="ED1", type_controlled=Authority.PERSON)
        editor_two = Authority.objects.create(name='EditorTwo', id="ED2", type_controlled=Authority.PERSON)
        ACRelation.objects.create(citation=citation, id="ACR1", authority=editor_one, type_controlled=ACRelation.EDITOR, data_display_order=1)
        ACRelation.objects.create(citation=citation, id="ACR2", authority=editor_two, type_controlled=ACRelation.EDITOR, data_display_order=2)
        expected1 = "ACR_ID ACR1 ACRStatus Active ACRType Editor ACRDisplayOrder 1.0 ACRNameForDisplayInCitation  AuthorityID ED1 AuthorityStatus Active AuthorityType Person AuthorityName EditorOne"
        expected2 = "ACR_ID ACR2 ACRStatus Active ACRType Editor ACRDisplayOrder 2.0 ACRNameForDisplayInCitation  AuthorityID ED2 AuthorityStatus Active AuthorityType Person AuthorityName EditorTwo"
        self.assertEqual(u'%s // %s' % (expected1, expected2), export.citation_editor(citation, []))

    def tearDown(self):
        Citation.objects.all().delete()
        Authority.objects.all().delete()
        ACRelation.objects.all().delete()


class TestCitationTitleColumn(unittest.TestCase):
    """
    The :func:`.export.citation_title` column retrieves the title of a
    :class:`.Citation` instance.
    """
    def test_citation_has_title(self):
        """
        The :class:`.Citation`\'s own title should be used, if it has one.
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)

        self.assertEqual(citation.title, export.citation_title(citation, []))

    def test_citation_is_review(self):
        """
        Many reviews don't have their own titles. We should use the title of the
        reviewed work to generate a title.
        """
        citation = Citation.objects.create(type_controlled=Citation.REVIEW)
        book = Citation.objects.create(title='Book',
                                       type_controlled=Citation.BOOK)
        CCRelation.objects.create(subject=book, object=citation,
                                  type_controlled=CCRelation.REVIEWED_BY)
        self.assertEqual('Review of "Book"', export.citation_title(citation, []))

    def test_citation_is_review_alt(self):
        """
        Many reviews don't have their own titles. We should use the title of the
        reviewed work to generate a title.
        """
        citation = Citation.objects.create(type_controlled=Citation.REVIEW)
        book = Citation.objects.create(title='Book',
                                       type_controlled=Citation.BOOK)
        CCRelation.objects.create(subject=citation, object=book,
                                  type_controlled=CCRelation.REVIEW_OF)
        self.assertEqual('Review of "Book"', export.citation_title(citation, []))

    def test_citation_is_review_missing_book(self):
        """
        Many reviews don't have their own titles. We should use the title of the
        reviewed work to generate a title.
        """
        citation = Citation.objects.create(type_controlled=Citation.REVIEW)

        self.assertEqual(u"Review of unknown publication",
                         export.citation_title(citation, []))


    def tearDown(self):
        Citation.objects.all().delete()
        CCRelation.objects.all().delete()


class TestPageNumbersAreForEveryone(unittest.TestCase):
    def test_pages(self):
        for ctype, _ in Citation.TYPE_CHOICES:
            citation = Citation.objects.create(type_controlled=ctype)
            citation.part_details = PartDetails.objects.create(page_begin=15, page_end=17)
            citation.save()
            if ctype == Citation.CHAPTER:
                self.assertTrue(export.pages(citation, []).startswith('pp.'))
            else:
                self.assertEqual(export.pages(citation, []), "15-17")

    def tearDown(self):
        Citation.objects.all().delete()
        CCRelation.objects.all().delete()

class TestPagesFreeTextAreExported(unittest.TestCase):
    def test_pages(self):
        for ctype, _ in Citation.TYPE_CHOICES:
            citation = Citation.objects.create(type_controlled=ctype)
            citation.part_details = PartDetails.objects.create(page_begin=15, page_end=17, pages_free_text='pages 15-17')
            citation.save()
            self.assertEqual("pages 15-17 (From 15 // To 17)", export.pages_free_text(citation, []))

    def tearDown(self):
        Citation.objects.all().delete()
        CCRelation.objects.all().delete()

class TestExtraRecordsAreAddedToTheExport(unittest.TestCase):
    """
    There are cases in which a column needs to add a related record to the
    export set.
    """
    def test_link_to_record_adds_extra_records(self):
        citation = Citation.objects.create(type_controlled=Citation.REVIEW)
        book = Citation.objects.create(title='Book',
                                       type_controlled=Citation.BOOK)
        CCRelation.objects.create(subject=citation, object=book,
                                  type_controlled=CCRelation.REVIEW_OF)
        extra = []
        export.link_to_record(citation, extra)
        self.assertEqual(len(extra), 1)
        self.assertEqual(extra[0].id, book.id)

    def test_link_to_record_results_in_extra_rows(self):
        citation = Citation.objects.create(type_controlled=Citation.REVIEW)
        book = Citation.objects.create(title='Book',
                                       type_controlled=Citation.BOOK)
        CCRelation.objects.create(subject=citation, object=book,
                                  type_controlled=CCRelation.REVIEW_OF)
        class FakeFile(object):
            def __init__(self):
                self.data = []

            def write(self, data):
                self.data.append(data)

        f = FakeFile()
        qs = Citation.objects.filter(pk=citation.id)
        export.generate_csv(f, qs, [export.object_id, export.link_to_record])
        self.assertEqual(len(f.data), 3)    # Including the header.
        self.assertTrue(book.id in zip(*[r.split(',') for r in f.data])[0][1:],
                        "Linked book record should be included in the output.")


    def tearDown(self):
        Citation.objects.all().delete()
        CCRelation.objects.all().delete()


class TestCitationSubjectColumn(unittest.TestCase):
    """
    The :func:`.export.subject` column retrieves subjects.
    """
    def test_citation_has_subject_with_config(self):
        """
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.THESIS)
        subject = Authority.objects.create(name='Test Authority', id='1C',
                                           type_controlled=Authority.CONCEPT)
        ACRelation.objects.create(citation=citation, authority=subject, id='ACR1',
                                  type_controlled=ACRelation.SUBJECT)

        expected = "ACR_ID ACR1 || ACRStatus Active || ACRType Subject || ACRDisplayOrder 1.0 || ACRNameForDisplayInCitation  || AuthorityID 1C || AuthorityStatus Active || AuthorityType Concept || AuthorityName Test Authority"
        self.assertEqual(expected, export.subjects(citation, [], config={'authority_delimiter': " || "}))

    def test_citation_has_subject_no_config(self):
        """
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.THESIS)
        subject = Authority.objects.create(name='Test Authority', id='1',
                                           type_controlled=Authority.CONCEPT)
        ACRelation.objects.create(citation=citation, authority=subject, id='ACR1',
                                  type_controlled=ACRelation.SUBJECT)

        expected = "ACR_ID ACR1 ACRStatus Active ACRType Subject ACRDisplayOrder 1.0 ACRNameForDisplayInCitation  AuthorityID 1 AuthorityStatus Active AuthorityType Concept AuthorityName Test Authority"
        self.assertEqual(expected, export.subjects(citation, []))

    def test_citation_has_school_with_config(self):
        """
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.THESIS)
        subject = Authority.objects.create(name='Test Authority', id='AU1C',
                                           type_controlled=Authority.INSTITUTION)
        ACRelation.objects.create(citation=citation, authority=subject, id='ACR1',
                                  type_controlled=ACRelation.SCHOOL)

        expected = "ACR_ID ACR1 || ACRStatus Active || ACRType School || ACRDisplayOrder 1.0 || ACRNameForDisplayInCitation  || AuthorityID AU1C || AuthorityStatus Active || AuthorityType Institution || AuthorityName Test Authority"
        self.assertEqual(expected, export.school(citation, [], config={'authority_delimiter': " || "}))

    def test_citation_has_school_no_config(self):
        """
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.THESIS)
        subject = Authority.objects.create(name='Test Authority', id='AU1',
                                           type_controlled=Authority.INSTITUTION)
        ACRelation.objects.create(citation=citation, authority=subject, id='ACR1',
                                  type_controlled=ACRelation.SCHOOL)

        expected = "ACR_ID ACR1 ACRStatus Active ACRType School ACRDisplayOrder 1.0 ACRNameForDisplayInCitation  AuthorityID AU1 AuthorityStatus Active AuthorityType Institution AuthorityName Test Authority"
        self.assertEqual(expected, export.school(citation, []))

    def tearDown(self):
        Citation.objects.all().delete()
        ACRelation.objects.all().delete()


class TestCitationAdvisorColumn(unittest.TestCase):
    """
    The :func:`.export.advisor` column retrieves advisors.
    """
    def test_citation_has_subject_with_config(self):
        """
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.THESIS)
        subject = Authority.objects.create(name='Test Authority', id='AU1C',
                                           type_controlled=Authority.PERSON)
        ACRelation.objects.create(citation=citation, authority=subject, id='ACR1',
                                  type_controlled=ACRelation.ADVISOR)

        expected = "ACR_ID ACR1 || ACRStatus Active || ACRType Advisor || ACRDisplayOrder 1.0 || ACRNameForDisplayInCitation  || AuthorityID AU1C || AuthorityStatus Active || AuthorityType Person || AuthorityName Test Authority"
        self.assertEqual(expected, export.advisor(citation, [], config={'authority_delimiter': " || "}))

    def test_citation_has_subject_no_config(self):
        """
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.THESIS)
        subject = Authority.objects.create(name='Test Authority', id='AU1',
                                           type_controlled=Authority.PERSON)
        ACRelation.objects.create(citation=citation, authority=subject, id='ACR1',
                                  type_controlled=ACRelation.ADVISOR)

        expected = "ACR_ID ACR1 ACRStatus Active ACRType Advisor ACRDisplayOrder 1.0 ACRNameForDisplayInCitation  AuthorityID AU1 AuthorityStatus Active AuthorityType Person AuthorityName Test Authority"
        self.assertEqual(expected, export.advisor(citation, []))


    def tearDown(self):
        Citation.objects.all().delete()
        ACRelation.objects.all().delete()


class TestIncludesSeriesArticleColumn(unittest.TestCase):
    """
    The INCLUDES_SERIES_ARTICLE relation actually represents its inverse.
    """
    def test_citation_has_subject(self):
        """
        """
        book = Citation.objects.create(title='The book title',
                                       type_controlled=Citation.BOOK)
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)

        CCRelation.objects.create(subject=book, object=citation,
                                  type_controlled=CCRelation.INCLUDES_SERIES_ARTICLE)

        extras = []
        value = export.include_series_article(citation, extras)
        self.assertEqual(value, book.id)
        self.assertEqual(len(extras), 1)
        self.assertEqual(extras[0].id, book.id)


    def tearDown(self):
        Citation.objects.all().delete()
        CCRelation.objects.all().delete()


class TestTrackingColumn(unittest.TestCase):
    """
    Tests export columns based on :class:`.Tracing` records.
    """
    def test_fully_entered(self):
        """
        """
        book = Citation.objects.create(title='The book title',
                                       type_controlled=Citation.BOOK)
        test_value = 'test'
        t = Tracking.objects.create(citation=book,
                                type_controlled=Tracking.FULLY_ENTERED,
                                tracking_info=test_value,
                                )


        value = export.fully_entered(book, [])
        expected = "%s: %s"%(t.id, t.modified_on)
        self.assertEqual(value, expected)

    def test_proofed(self):
        """
        """
        book = Citation.objects.create(title='The book title',
                                       type_controlled=Citation.BOOK)
        test_value = 'test'
        t = Tracking.objects.create(citation=book,
                                type_controlled=Tracking.PROOFED,
                                tracking_info=test_value)

        value = export.proofed(book, [])
        expected = "%s: %s"%(t.id, t.modified_on)
        self.assertEqual(value, expected)

    def test_spw_checked(self):
        """
        """
        book = Citation.objects.create(title='The book title',
                                       type_controlled=Citation.BOOK)
        test_value = 'test'
        t = Tracking.objects.create(citation=book,
                                type_controlled=Tracking.AUTHORIZED,
                                tracking_info=test_value)

        value = export.spw_checked(book, [])
        expected = "%s: %s"%(t.id, t.modified_on)
        self.assertEqual(value, expected)

    def test_published_print(self):
        """
        """
        book = Citation.objects.create(title='The book title',
                                       type_controlled=Citation.BOOK)
        test_value = 'test'
        t = Tracking.objects.create(citation=book,
                                type_controlled=Tracking.PRINTED,
                                tracking_info=test_value)

        value = export.published_print(book, [])
        expected = "%s: %s"%(t.id, t.modified_on)
        self.assertEqual(value, expected)

    def test_published_rlg(self):
        """
        """
        book = Citation.objects.create(title='The book title',
                                       type_controlled=Citation.BOOK)
        test_value = 'test'
        t = Tracking.objects.create(citation=book,
                                type_controlled=Tracking.HSTM_UPLOAD,
                                tracking_info=test_value)

        value = export.published_rlg(book, [])
        expected = "%s: %s"%(t.id, t.modified_on)
        self.assertEqual(value, expected)

    def tearDown(self):
        Citation.objects.all().delete()
        CCRelation.objects.all().delete()
        Tracking.objects.all().delete()


if __name__ == '__main__':
    unittest.main()
