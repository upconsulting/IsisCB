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
        test_fnx = mock.Mock(side_effect=lambda o, e: o)
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

    def test_citation_has_single_author(self):
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        author = Authority.objects.create(name='Author', type_controlled=Authority.PERSON)
        ACRelation.objects.create(citation=citation, authority=author, type_controlled=ACRelation.AUTHOR)
        self.assertEqual(author.name, export.citation_author(citation, []))

    def test_citation_has_single_author_with_display_name(self):
        """
        If the ``name_for_display_in_citation`` field is filled on the
        authorship :class:`.ACRelation`\, its value should be preferred.
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        author = Authority.objects.create(name='Author', type_controlled=Authority.PERSON)
        relation = ACRelation.objects.create(citation=citation, authority=author, type_controlled=ACRelation.AUTHOR, name_for_display_in_citation='Some other name')
        self.assertEqual(relation.name_for_display_in_citation, export.citation_author(citation, []))

    def test_citation_has_multiple_authors(self):
        """
        Multiple authors should be separated by semi-colons.
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        author_one = Authority.objects.create(name='AuthorOne', type_controlled=Authority.PERSON)
        author_two = Authority.objects.create(name='AuthorTwo', type_controlled=Authority.PERSON)
        ACRelation.objects.create(citation=citation, authority=author_one, type_controlled=ACRelation.AUTHOR, data_display_order=1)
        ACRelation.objects.create(citation=citation, authority=author_two, type_controlled=ACRelation.AUTHOR, data_display_order=2)
        self.assertEqual(u'%s; %s' % (author_one.name, author_two.name), export.citation_author(citation, []))

    def tearDown(self):
        Citation.objects.all().delete()
        Authority.objects.all().delete()
        ACRelation.objects.all().delete()


class TestCitationEditorColumn(unittest.TestCase):
    """
    The :func:`.export.citation_editor` column retrieves the names of the
    editor(s) of a citation.
    """

    def test_citation_has_single_editor(self):
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        editor = Authority.objects.create(name='Editor', type_controlled=Authority.PERSON)
        ACRelation.objects.create(citation=citation, authority=editor, type_controlled=ACRelation.EDITOR)
        self.assertEqual(editor.name, export.citation_editor(citation, []))

    def test_citation_has_single_author_with_display_name(self):
        """
        If the ``name_for_display_in_citation`` field is filled on the
        authorship :class:`.ACRelation`\, its value should be preferred.
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        editor = Authority.objects.create(name='Editor', type_controlled=Authority.PERSON)
        relation = ACRelation.objects.create(citation=citation, authority=editor, type_controlled=ACRelation.EDITOR, name_for_display_in_citation='Some other name')
        self.assertEqual(relation.name_for_display_in_citation, export.citation_editor(citation, []))

    def test_citation_has_multiple_authors(self):
        """
        Multiple editors should be separated by semi-colons.
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        editor_one = Authority.objects.create(name='EditorOne', type_controlled=Authority.PERSON)
        editor_two = Authority.objects.create(name='EditorTwo', type_controlled=Authority.PERSON)
        ACRelation.objects.create(citation=citation, authority=editor_one, type_controlled=ACRelation.EDITOR, data_display_order=1)
        ACRelation.objects.create(citation=citation, authority=editor_two, type_controlled=ACRelation.EDITOR, data_display_order=2)
        self.assertEqual(u'%s; %s' % (editor_one.name, editor_two.name), export.citation_editor(citation, []))

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
    def test_citation_has_subject(self):
        """
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.THESIS)
        subject = Authority.objects.create(name='Test Authority',
                                           type_controlled=Authority.CONCEPT)
        ACRelation.objects.create(citation=citation, authority=subject,
                                  type_controlled=ACRelation.SUBJECT)

        self.assertEqual(subject.name, export.subjects(citation, []))

    def test_citation_has_school(self):
        """
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.THESIS)
        subject = Authority.objects.create(name='Test Authority',
                                           type_controlled=Authority.INSTITUTION)
        ACRelation.objects.create(citation=citation, authority=subject,
                                  type_controlled=ACRelation.SCHOOL)

        self.assertEqual(subject.name, export.school(citation, []))

    def tearDown(self):
        Citation.objects.all().delete()
        ACRelation.objects.all().delete()


class TestCitationAdvisorColumn(unittest.TestCase):
    """
    The :func:`.export.advisor` column retrieves advisors.
    """
    def test_citation_has_subject(self):
        """
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.THESIS)
        subject = Authority.objects.create(name='Test Authority',
                                           type_controlled=Authority.PERSON)
        ACRelation.objects.create(citation=citation, authority=subject,
                                  type_controlled=ACRelation.ADVISOR)

        self.assertEqual(subject.name, export.advisor(citation, []))


    def tearDown(self):
        Citation.objects.all().delete()
        ACRelation.objects.all().delete()


if __name__ == '__main__':
    unittest.main()
