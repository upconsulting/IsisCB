import unittest

from isisdata.models import ACRelation


class TestACRelationTypeControls(unittest.TestCase):
    def test_personal_responsibility(self):
        acrelation = ACRelation.objects.create(type_controlled=ACRelation.AUTHOR)
        self.assertEqual(acrelation.type_broad_controlled, ACRelation.PERSONAL_RESPONS)

    def test_subject_content(self):
        acrelation = ACRelation.objects.create(type_controlled=ACRelation.SUBJECT)
        self.assertEqual(acrelation.type_broad_controlled, ACRelation.SUBJECT_CONTENT)

    def test_institution(self):
        acrelation = ACRelation.objects.create(type_controlled=ACRelation.SCHOOL)
        self.assertEqual(acrelation.type_broad_controlled, ACRelation.INSTITUTIONAL_HOST)

    def test_publication(self):
        acrelation = ACRelation.objects.create(type_controlled=ACRelation.PERIODICAL)
        self.assertEqual(acrelation.type_broad_controlled, ACRelation.PUBLICATION_HOST)

if __name__ == '__main__':
    unittest.main()
