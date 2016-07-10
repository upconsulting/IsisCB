import unittest

from isisdata.models import *

authority_data = {
    'name': 'testAuthority',
    'type_controlled': Authority.PERSON,
}

citation_data = {
    'title': 'testCitation',
    'type_controlled': Citation.ARTICLE,
}

acrelation_data = {
    'type_controlled': ACRelation.AUTHOR
}


class TestAuthorityRecordStatus(unittest.TestCase):
    def test_create(self):
        authority = Authority(
            record_status_value=CuratedMixin.ACTIVE,
            **authority_data
        )
        authority.save()
        self.assertTrue(authority.public)

    def test_create_record_status_default(self):
        authority = Authority.objects.create(
            **authority_data
        )
        self.assertTrue(authority.public)

    def test_create_record_status_active(self):
        authority = Authority.objects.create(
            record_status_value=CuratedMixin.ACTIVE,
            **authority_data
        )
        self.assertTrue(authority.public)

    def test_create_record_status_inactive(self):
        authority = Authority.objects.create(
            record_status_value=CuratedMixin.INACTIVE,
            **authority_data
        )
        self.assertFalse(authority.public)

    def test_change_record_status_active(self):
        authority = Authority.objects.create(
            record_status_value=CuratedMixin.INACTIVE,
            **authority_data
        )
        authority.record_status_value = CuratedMixin.ACTIVE
        authority.save()
        self.assertTrue(authority.public)

    def test_change_record_status_inactive(self):
        authority = Authority.objects.create(
            record_status_value=CuratedMixin.ACTIVE,
            **authority_data
        )
        authority.record_status_value = CuratedMixin.INACTIVE
        authority.save()
        self.assertFalse(authority.public)


class TestCitationRecordStatus(unittest.TestCase):
    def test_create_record_status_default(self):
        citation = Citation.objects.create(
            **citation_data
        )
        self.assertTrue(citation.public)

    def test_create_record_status_active(self):
        citation = Citation.objects.create(
            record_status_value=CuratedMixin.ACTIVE,
            **citation_data
        )
        self.assertTrue(citation.public)

    def test_create_record_status_inactive(self):
        citation = Citation.objects.create(
            record_status_value=CuratedMixin.INACTIVE,
            **citation_data
        )
        self.assertFalse(citation.public)

    def test_change_record_status_active(self):
        citation = Citation.objects.create(
            record_status_value=CuratedMixin.INACTIVE,
            **citation_data
        )
        citation.record_status_value = CuratedMixin.ACTIVE
        citation.save()
        self.assertTrue(citation.public)

    def test_change_record_status_inactive(self):
        citation = Citation.objects.create(
            record_status_value=CuratedMixin.ACTIVE,
            **citation_data
        )
        citation.record_status_value = CuratedMixin.INACTIVE
        citation.save()
        self.assertFalse(citation.public)


class TestACRelationRecordStatus(unittest.TestCase):
    def setUp(self):
        self.authority = Authority.objects.create(**authority_data)
        self.citation = Citation.objects.create(**citation_data)

    def test_create_record_status_default(self):
        acrelation = ACRelation.objects.create(
            authority=self.authority,
            citation=self.citation,
            **acrelation_data
        )
        self.assertTrue(acrelation.public)

    def test_create_record_status_active(self):
        acrelation = ACRelation.objects.create(
            authority=self.authority,
            citation=self.citation,
            record_status_value=CuratedMixin.ACTIVE,
            **acrelation_data
        )
        self.assertTrue(acrelation.public)

    def test_create_record_status_inactive(self):
        acrelation = ACRelation.objects.create(
            authority=self.authority,
            citation=self.citation,
            record_status_value=CuratedMixin.INACTIVE,
            **acrelation_data
        )
        self.assertFalse(acrelation.public)

    def test_change_record_status_active(self):
        acrelation = ACRelation.objects.create(
            authority=self.authority,
            citation=self.citation,
            record_status_value=CuratedMixin.INACTIVE,
            **acrelation_data
        )
        acrelation.record_status_value = CuratedMixin.ACTIVE
        acrelation.save()
        self.assertTrue(acrelation.public)

    def test_change_record_status_inactive(self):
        acrelation = ACRelation.objects.create(
            authority=self.authority,
            citation=self.citation,
            record_status_value=CuratedMixin.ACTIVE,
            **acrelation_data
        )
        acrelation.record_status_value = CuratedMixin.INACTIVE
        acrelation.save()
        self.assertFalse(acrelation.public)
