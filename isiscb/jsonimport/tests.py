from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from jsonimport.models import (
    ImportedACRelation,
    ImportedAttribute,
    ImportedAuthority,
    ImportedCitation,
    ImportedDataset,
    ImportedLinkedData,
)
from jsonimport.tasks import (
    _create_ac_relation,
    _create_authority_attribute,
    _create_citation_attribute,
    _create_imported_authority_status,
    _create_imported_citation_status,
    _create_linkeddata,
    _get_authority_record_status,
    _get_authority_type,
    _get_citation_type,
)
from isisdata.models import ACRelation, AttributeType, Authority, CharValue, Citation, LinkedDataType, Tenant


class JsonImportTasksTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='import-tester', password='testpass')
        self.tenant = Tenant.objects.create(
            name='Test Tenant',
            title='Test Tenant',
            identifier='test-tenant',
        )
        self.dataset = ImportedDataset.objects.create(
            name='Test dataset',
            created_by=self.user,
            owning_tenant=self.tenant,
        )
        self.char_type = AttributeType.objects.create(
            name='TestChar',
            value_content_type=ContentType.objects.get_for_model(CharValue),
        )
        self.linked_data_type = LinkedDataType.objects.create(name='VIAF')

    def test_type_mapping_helpers(self):
        self.assertEqual(_get_citation_type('Book'), Citation.BOOK)
        self.assertEqual(_get_citation_type('unknown'), '')
        self.assertEqual(_get_authority_type('Person'), Authority.PERSON)
        self.assertEqual(_get_authority_type('missing'), '')
        self.assertEqual(_get_authority_record_status('active'), Authority.ACTIVE)
        self.assertEqual(_get_authority_record_status('duplicate'), Authority.DUPLICATE)

    def test_create_authority_attribute_persists_value(self):
        authority = ImportedAuthority.objects.create(
            name='Example Authority',
            dataset=self.dataset,
            local_dataset_id='AUTH-001',
            type_controlled=Authority.PERSON,
        )

        attribute = _create_authority_attribute('TestChar', 'Example value', authority, self.dataset, [])

        self.assertIsNotNone(attribute)
        self.assertEqual(attribute.value, 'Example value')
        self.assertEqual(attribute.attribute_type, self.char_type)
        self.assertEqual(ImportedAttribute.objects.filter(value_authority=authority).count(), 1)

    def test_create_citation_attribute_persists_value(self):
        citation = ImportedCitation.objects.create(
            dataset=self.dataset,
            local_dataset_id='CIT-001',
            title='Example Citation',
            type_controlled=Citation.BOOK,
        )

        attribute = _create_citation_attribute('TestChar', 'Example value', citation, self.dataset, [])

        self.assertIsNotNone(attribute)
        self.assertEqual(attribute.value, 'Example value')
        self.assertEqual(attribute.attribute_type, self.char_type)
        self.assertEqual(ImportedAttribute.objects.filter(value_citation=citation).count(), 1)

    def test_invalid_attribute_type_adds_error_status(self):
        authority = ImportedAuthority.objects.create(
            name='Bad Authority',
            dataset=self.dataset,
            local_dataset_id='AUTH-002',
            type_controlled=Authority.PERSON,
        )
        results = []

        attribute = _create_authority_attribute('MissingType', 'Nope', authority, self.dataset, results)

        self.assertIsNone(attribute)
        self.assertEqual(results[0][0], 'ERROR')
        self.assertEqual(results[0][1], 'Authority')

    def test_create_linkeddata_creates_record(self):
        authority = ImportedAuthority.objects.create(
            name='Linked Authority',
            dataset=self.dataset,
            local_dataset_id='AUTH-003',
            type_controlled=Authority.PERSON,
        )

        _create_linkeddata({'type': 'viaf', 'value': 'https://viaf.org/viaf/12345678'}, authority, [])

        linked_data = authority.linkeddata_entries.first()
        self.assertIsNotNone(linked_data)
        self.assertEqual(linked_data.universal_resource_name, 'https://viaf.org/viaf/12345678')
        self.assertEqual(linked_data.type_controlled, self.linked_data_type)

    def test_create_imported_status_helpers(self):
        authority = ImportedAuthority.objects.create(
            name='Status Authority',
            dataset=self.dataset,
            local_dataset_id='AUTH-004',
            type_controlled=Authority.PERSON,
        )
        citation = ImportedCitation.objects.create(
            dataset=self.dataset,
            local_dataset_id='CIT-004',
            title='Status Citation',
            type_controlled=Citation.BOOK,
        )
        results = []

        _create_imported_authority_status(self.dataset, 'SUCCESS', 'Authority ok', results, authority)
        _create_imported_citation_status(self.dataset, 'WARNING', 'Citation warning', results, citation)

        self.assertEqual(results[0][0], 'SUCCESS')
        self.assertEqual(results[1][0], 'WARNING')
        self.assertEqual(results[0][3], 'Authority ok')
        self.assertEqual(results[1][3], 'Citation warning')

    def test_create_ac_relation_creates_imported_relation(self):
        authority = Authority.objects.create(
            name='Related Authority',
            type_controlled=Authority.PERSON,
        )
        citation = ImportedCitation.objects.create(
            dataset=self.dataset,
            local_dataset_id='CIT-005',
            title='Relation Citation',
            type_controlled=Citation.BOOK,
        )
        results = []

        _create_ac_relation(
            {
                'cba_id': str(authority.pk),
                'relationship_type': 'author',
                'display_name': 'Related Authority',
                'order': 1,
            },
            {},
            citation,
            results,
            type_controlled=None,
        )

        relation = ImportedACRelation.objects.filter(citation=citation).first()
        self.assertIsNotNone(relation)
        self.assertEqual(relation.authority, None)
        self.assertEqual(relation.existing_authority, authority)
        self.assertEqual(relation.type_controlled, ACRelation.AUTHOR)
        self.assertEqual(results[0][0], 'SUCCESS')
