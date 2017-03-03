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
        test_fnx = mock.Mock(side_effect=lambda o: o)
        test_column = export.Column('Test', test_fnx)
        self.assertEqual('foo', test_column('foo'))
        self.assertEqual(test_fnx.call_count, 1)

    def test_column_enforces_input_expectation(self):
        """
        If a :class:`.Column` is instantiated with a specific input expectation
        (e.g. a model class), that expectation should be enforced when the
        column is called.
        """

        test_fnx = mock.Mock(side_effect=lambda o: o + 1)
        test_column = export.Column('Test', test_fnx, int)
        with self.assertRaises(AssertionError):
            test_column('Definitely not an int')
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
        self.assertEqual(author.name, export.citation_author(citation))

    def test_citation_has_single_author_with_display_name(self):
        """
        If the ``name_for_display_in_citation`` field is filled on the
        authorship :class:`.ACRelation`\, its value should be preferred.
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        author = Authority.objects.create(name='Author', type_controlled=Authority.PERSON)
        relation = ACRelation.objects.create(citation=citation, authority=author, type_controlled=ACRelation.AUTHOR, name_for_display_in_citation='Some other name')
        self.assertEqual(relation.name_for_display_in_citation, export.citation_author(citation))

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
        self.assertEqual(u'%s; %s' % (author_one.name, author_two.name), export.citation_author(citation))

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
        self.assertEqual(editor.name, export.citation_editor(citation))

    def test_citation_has_single_author_with_display_name(self):
        """
        If the ``name_for_display_in_citation`` field is filled on the
        authorship :class:`.ACRelation`\, its value should be preferred.
        """
        citation = Citation.objects.create(title='The title',
                                           type_controlled=Citation.ARTICLE)
        editor = Authority.objects.create(name='Editor', type_controlled=Authority.PERSON)
        relation = ACRelation.objects.create(citation=citation, authority=editor, type_controlled=ACRelation.EDITOR, name_for_display_in_citation='Some other name')
        self.assertEqual(relation.name_for_display_in_citation, export.citation_editor(citation))

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
        self.assertEqual(u'%s; %s' % (editor_one.name, editor_two.name), export.citation_editor(citation))

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

        self.assertEqual(citation.title, export.citation_title(citation))

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
        self.assertEqual('Review of "Book"', export.citation_title(citation))

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
        self.assertEqual('Review of "Book"', export.citation_title(citation))

    def test_citation_is_review_missing_book(self):
        """
        Many reviews don't have their own titles. We should use the title of the
        reviewed work to generate a title.
        """
        citation = Citation.objects.create(type_controlled=Citation.REVIEW)

        self.assertEqual(u"Review of unknown publication",
                         export.citation_title(citation))


    def tearDown(self):
        Citation.objects.all().delete()
        CCRelation.objects.all().delete()


if __name__ == '__main__':
    unittest.main()
