# coding=utf-8

from django.core.management import call_command
from django.contrib.contenttypes.models import ContentType

import unittest
import os
import datetime
import pytz
from collections import Counter

from isisdata.models import *
from isisdata.management.commands.filemaker_update import FMPDSOParser, DatabaseHandler

DATETIME_FIELDS = [
    'created_on_fm',
]

CURATION_FIELDS = [
    'created_by_fm',
]

UTC = pytz.UTC


class TestHandler(object):
    """
    Just for testing.
    """
    def __init__(self, testcase, *args, **kwargs):
        super(TestHandler, self).__init__(*args, **kwargs)
        self.testcase = testcase

    def handle_attribute(self, fielddata, extra):
        keys, values = zip(*fielddata)

        self.testcase.assertEqual(Counter(keys)['value'], Counter(keys)['type_qualifier'])


    def handle_citation(self, fielddata, extra):
        data = dict(fielddata)
        if data['id'] == 'ACR000000001':
            self.testcase.assertEqual(data['authority_id'], 'CBA000087646')
            self.testcase.assertEqual(data['citation_id'], 'CBB000111626')
            self.testcase.assertEqual(data['modified_by_fm'], 'spw')
            self.testcase.assertEqual(data['created_on_fm'], datetime.datetime(2015, 5, 20, 15, 55, 0))
            self.testcase.assertEqual(data['modified_on_fm'], datetime.datetime(2016, 6, 2, 16, 6, 6))
            self.testcase.assertEqual(data['name_for_display_in_citation'], u'Rousseau, Jean-Jacques')
            self.testcase.assertEqual(data['personal_name_first'], u'Jean-Jacques')
            self.testcase.assertEqual(data['personal_name_last'], u'Rousseau')
            self.testcase.assertNotEqual(data['record_history'], '')
            self.testcase.assertEqual(data['record_status_value'], CuratedMixin.ACTIVE)
            self.testcase.assertTrue(data['public'])
            self.testcase.assertTrue(data['type_broad_controlled'], ACRelation.HASPERSONALRESPONSIBILITYFOR)
            self.testcase.assertEqual(data['type_controlled'], ACRelation.AUTHOR)
        elif data['id'] == 'ACR000000002':
            self.testcase.assertEqual(data['type_controlled'], ACRelation.EDITOR)
        elif data['id'] == 'ACR000000003':
            self.testcase.assertEqual(data['created_by_fm'], 'spweldon')
            self.testcase.assertEqual(data['type_controlled'], ACRelation.CONTRIBUTOR)
            self.testcase.assertEqual(data['data_display_order'], '50.002')
        elif data['id'] == 'ACR000000006':
            self.testcase.assertEqual(data['type_controlled'], ACRelation.AUTHOR)

    def handle_citation(self, fielddata, extra):
        data = dict(fielddata)

        if data['id'] == 'CBB000111626':
            self.testcase.assertEqual(data['modified_by_fm'], 'admin')
            self.testcase.assertEqual(data['created_on_fm'], datetime.datetime(2003, 7, 15, 0, 0, 0))
            self.testcase.assertEqual(data['modified_on_fm'], datetime.datetime(2016, 5, 12, 14, 7, 52))
            self.testcase.assertEqual(data['dataset'], 'Isis Bibliography of the History of Science (Joy Harvey, ed.)')
            self.testcase.assertNotEqual(data['edition_details'], '')
            self.testcase.assertNotEqual(data['record_history'], '')
            self.testcase.assertEqual(data['language'], 'en')
            self.testcase.assertEqual(data['type_controlled'], Citation.BOOK)
            self.testcase.assertEqual(data['record_status_value'], CuratedMixin.ACTIVE)
            self.testcase.assertTrue(data['public'])
            self.testcase.assertEqual(data['title'], u'The Reveries of the Solitary Walker, Botanical Writings, and Letters to Franquières')
        elif data['id'] == 'CBB000110001':
            self.testcase.assertNotEqual(data['physical_details'], '')
        elif data['id'] == 'CBB000110002':
            self.testcase.assertNotEqual(data['description'], '')
        elif data['id'] == 'CBB000110004':
            self.testcase.assertEqual(data['language'], 'fr')
            self.testcase.assertEqual(data['type_controlled'], Citation.ARTICLE)
            pdata = dict(extra[0])
            self.testcase.assertEqual(pdata['page_begin'], 295)
            self.testcase.assertEqual(pdata['pages_free_text'], '295--304')

    def handle_authority(self, fielddata, extra):
        data = dict(fielddata)
        if data['id'] == 'CBA000167135':
            self.testcase.assertEqual(data['created_by_fm'], 'admin')
            self.testcase.assertEqual(data['created_on_fm'], datetime.datetime(2016, 5, 20, 11, 10, 29))
            self.testcase.assertEqual(data['name'], 'Perugia: Edizioni Centro Stampa')
            self.testcase.assertNotEqual(data['record_history'], '')
            self.testcase.assertTrue(data['public'])
            self.testcase.assertEqual(data['record_status_value'], CuratedMixin.ACTIVE)
            self.testcase.assertEqual(data['type_controlled'], Authority.PUBLISHER)
        elif data['id'] == 'CBA000167056':
            self.testcase.assertEqual(data['type_controlled'], Authority.PERSON)
        elif data['id'] == 'CBA000166688':
            self.testcase.assertEqual(data['type_controlled'], Authority.INSTITUTION)
        elif data['id'] == 'CBA000165193':
            self.testcase.assertEqual(data['type_controlled'], Authority.GEOGRAPHIC_TERM)
        elif data['id'] == 'CBA000165190':
            self.testcase.assertEqual(data['type_controlled'], Authority.CONCEPT)
        elif data['id'] == 'CBA000031356':
            self.testcase.assertEqual(data['record_status_value'], CuratedMixin.INACTIVE)
            self.testcase.assertEqual(data['type_controlled'], Authority.PERSON)


class TestLoadFileMaker(unittest.TestCase):
    def setUp(self):
        call_command('loaddata', 'language.json')
        call_command('loaddata', 'linkeddatatypes.json')
        self.handler = TestHandler(self)

    def test_handle_record_status(self):
        public, status, explanation = FMPDSOParser._handle_record_status('authority', 'record_status', 'Inactive')
        self.assertFalse(public)
        self.assertEqual(status, 'Inactive')
        self.assertEqual(explanation, '')

    def test_map_field_value(self):
        parser = FMPDSOParser(dict())
        result = dict(parser._map_field_value('authority', 'RecordStatus', 'Inactive'))
        self.assertFalse(result['public'])
        self.assertEqual(result['record_status_value'], 'Inactive')

    def test_handle_language(self):
        parser = FMPDSOParser(dict())
        result = parser._handle_language('authority', 'Language', 'English')
        self.assertEqual(result, 'en')

    def test_parse_authority(self):
        parser = FMPDSOParser(self.handler)
        parser.parse('authority', 'isisdata/tests/data/chunked/authority.xml', ['person'])

    def test_parse_citation(self):
        parser = FMPDSOParser(self.handler)
        parser.parse('citation', 'isisdata/tests/data/chunked/citation.xml', ['partdetails'])

    def test_parse_acrelation(self):
        parser = FMPDSOParser(self.handler)
        parser.parse('acrelation', 'isisdata/tests/data/chunked/acrelation.xml', [])

    def test_parse_attribute(self):
        parser = FMPDSOParser(self.handler)
        parser.parse('attribute', 'isisdata/tests/data/chunked/attribute.xml', [])

    def tearDown(self):
        Value.objects.all().delete()
        DateTimeValue.objects.all().delete()
        DateRangeValue.objects.all().delete()
        AttributeType.objects.all().delete()
        Attribute.objects.all().delete()
        ACRelation.objects.all().delete()
        CCRelation.objects.all().delete()
        Authority.objects.all().delete()
        Citation.objects.all().delete()
        LinkedData.objects.all().delete()

        Language.objects.all().delete()
        LinkedDataType.objects.all().delete()


class TestLoadFileMakerDatabase(unittest.TestCase):
    def setUp(self):
        call_command('loaddata', 'language.json')
        call_command('loaddata', 'linkeddatatypes.json')
        self.parser = FMPDSOParser(DatabaseHandler())

    def test_parse_authority(self):
        self.parser.parse('authority', 'isisdata/tests/data/chunked/authority.xml', ['person'])
        authority = Authority.objects.get(pk='CBA000167135')
        self.assertEqual(authority.created_by_fm, 'admin')
        self.assertEqual(authority.name, 'Perugia: Edizioni Centro Stampa')
        self.assertNotEqual(authority.record_history, '')
        self.assertTrue(authority.public)
        self.assertEqual(authority.record_status_value, CuratedMixin.ACTIVE)
        self.assertEqual(authority.type_controlled, Authority.PUBLISHER)

    def test_parse_attribute(self):
        # Try to trip things up by creating back AttributeTypes ahead of time.
        AttributeType.objects.create(
            name='PublicationDate',
            display_name='Publication Date',
            value_content_type=ContentType.objects.get_for_model(DateValue)
        )
        AttributeType.objects.create(
            name='BirthToDeathDates',
            display_name='BirthToDeathDates',
            value_content_type=ContentType.objects.get_for_model(DateValue)
        )

        citations = [
            'CBB000111626', 'CBB000110001', 'CBB000110002', 'CBB000110003',
            'CBB000110004', 'CBB000110005' 'CBB000110006', 'CBB000110007',
            'CBB000110008', 'CBB000110009', 'CBB000110010', 'CBB000110011',
            'CBB000110012']
        authorities = [
            'CBA000073481', 'CBA000018872', 'CBA000019231', 'CBA000060556',
            'CBA000042082',
        ]
        for citation_id in citations:
            Citation.objects.create(
                id=citation_id,
                type_controlled=Citation.ARTICLE,
                title='A Test Citation'
            )
        for authority_id in authorities:
            Authority.objects.create(
                id=authority_id,
                type_controlled=Authority.PERSON,
                name='A Test Authority'
            )
        self.parser.parse('attribute', 'isisdata/tests/data/chunked/attribute.xml', [])
        attribute = Attribute.objects.get(pk='ATT000204037')
        self.assertEqual(attribute.source_instance_id, 'CBA000042082')
        self.assertIsInstance(attribute.value.get_child_class(), ISODateRangeValue)
        self.assertEqual(attribute.value.get_child_class().value, [[1916]])
        self.assertEqual(
            attribute.type_controlled.value_content_type.id,
            ContentType.objects.get_for_model(ISODateRangeValue).id)

        attribute = Attribute.objects.get(pk='ATT000204034')
        self.assertEqual(attribute.source_instance_id, 'CBA000018872')
        self.assertIsInstance(attribute.value.get_child_class(), ISODateRangeValue)
        self.assertEqual(attribute.value.get_child_class().value, [[1916], [1972]])
        self.assertEqual(
            attribute.type_controlled.value_content_type.id,
            ContentType.objects.get_for_model(ISODateRangeValue).id)

        attribute = Attribute.objects.get(pk='ATT000000021')
        self.assertEqual(attribute.source_instance_id, 'CBB000110012')
        self.assertIsInstance(attribute.value.get_child_class(), ISODateValue)
        self.assertEqual(attribute.value.get_child_class().value, [2000])
        self.assertEqual(
            attribute.type_controlled.value_content_type.id,
            ContentType.objects.get_for_model(ISODateValue).id)

        attribute = Attribute.objects.get(pk='ATT000000009')
        self.assertEqual(attribute.value.cvalue(), [2000, 5, 3])


    def tearDown(self):
        Value.objects.all().delete()
        DateTimeValue.objects.all().delete()
        DateRangeValue.objects.all().delete()
        AttributeType.objects.all().delete()
        Attribute.objects.all().delete()
        ACRelation.objects.all().delete()
        CCRelation.objects.all().delete()
        Authority.objects.all().delete()
        Citation.objects.all().delete()

        Language.objects.all().delete()
        LinkedDataType.objects.all().delete()
        LinkedData.objects.all().delete()


class TestLoadFileMakerFull(unittest.TestCase):
    def setUp(self):
        call_command('loaddata', 'language.json')
        # call_command('loaddata', 'linkeddatatypes.json')

    def tearDown(self):
        Value.objects.all().delete()
        DateTimeValue.objects.all().delete()
        DateRangeValue.objects.all().delete()
        AttributeType.objects.all().delete()
        Attribute.objects.all().delete()
        ACRelation.objects.all().delete()
        CCRelation.objects.all().delete()
        Authority.objects.all().delete()
        Citation.objects.all().delete()

        Language.objects.all().delete()
        LinkedDataType.objects.all().delete()
        LinkedData.objects.all().delete()


    def test_load_authorities(self):
        call_command('filemaker_update', 'isisdata/tests/data', 'authority')

        self.assertEqual(Authority.objects.count(), 3)
        for instance in Authority.objects.all():
            self.assertGreater(len(instance.name), 0)
            self.assertGreater(len(instance.description), 0)
            self.assertGreater(len(instance.classification_system), 0)
            self.assertGreater(len(instance.classification_code), 0)
            self.assertGreater(len(instance.classification_hierarchy), 0)
            self.assertGreater(len(instance.record_status_value), 0)
            self.assertGreater(len(instance.classification_system), 0)
            for field in CURATION_FIELDS:
                self.assertGreater(len(getattr(instance, field)), 0)
            for field in DATETIME_FIELDS:
                now = UTC.localize(datetime.datetime.now())
                then = getattr(instance, field)
                self.assertGreater(now, then)

            print 'record_status_value', instance.record_status_value
            if instance.record_status_value == 'RD':
                self.assertTrue(instance.redirect_to is not None)

    def test_load_citations(self):
        call_command('filemaker_update', 'isisdata/tests/data', 'citation')

        self.assertEqual(Citation.objects.count(), 2)

        for instance in Citation.objects.all():
            self.assertGreater(len(instance.title), 0)
            self.assertGreater(len(instance.description), 0)
            self.assertGreater(len(instance.type_controlled), 0)
            self.assertGreater(len(instance.abstract), 0)
            self.assertGreater(len(instance.edition_details), 0)
            self.assertGreater(len(instance.physical_details), 0)
            self.assertGreater(instance.language.count(), 0)
            for field in CURATION_FIELDS:
                self.assertGreater(len(getattr(instance, field)), 0)
            for field in DATETIME_FIELDS:
                now = UTC.localize(datetime.datetime.now())
                then = getattr(instance, field)
                self.assertGreater(now, then)

        # Sometimes nasty non-integer data ends up in fields that should have
        #  integers only. These should get pushed off into the corresponding
        #  free_text field.
        instance = Citation.objects.get(pk='CBB000000002')
        self.assertGreater(len(instance.part_details.issue_free_text), 0)
        self.assertEqual(instance.part_details.issue_free_text, '32B')
        self.assertEqual(instance.part_details.issue_begin, None)

    def test_load_attributes(self):
        call_command('filemaker_update', 'isisdata/tests/data', 'citation')
        call_command('filemaker_update', 'isisdata/tests/data', 'authority')
        call_command('filemaker_update', 'isisdata/tests/data', 'attribute')

        self.assertEqual(Attribute.objects.count(), 2)
        self.assertEqual(Value.objects.count(), 2)

        for instance in Attribute.objects.all():
            self.assertTrue(instance.source_content_type_id is not None)
            self.assertTrue(instance.source_instance_id is not None)
            self.assertGreater(len(instance.value_freeform), 0)
            for field in CURATION_FIELDS:
                self.assertGreater(len(getattr(instance, field)), 0)
            for field in DATETIME_FIELDS:
                now = UTC.localize(datetime.datetime.now())
                then = getattr(instance, field)
                self.assertGreater(now, then)

        for instance in Value.objects.all():
            child = instance.get_child_class()
            self.assertTrue(child.value is not None)
            self.assertTrue(child.attribute_id is not None)

    def test_load_linked_data(self):

        call_command('filemaker_update', 'isisdata/tests/data', 'citation')
        call_command('filemaker_update', 'isisdata/tests/data', 'authority')
        call_command('filemaker_update', 'isisdata/tests/data', 'linkeddata')

        self.assertEqual(LinkedData.objects.count(), 2)

        for instance in LinkedData.objects.all():
            self.assertTrue(instance.universal_resource_name is not None)
            self.assertTrue(instance.type_controlled is not None)
            for field in CURATION_FIELDS:
                if field in ['record_action']:
                    continue
                self.assertGreater(len(getattr(instance, field)), 0)
            for field in DATETIME_FIELDS:
                now = UTC.localize(datetime.datetime.now())
                then = getattr(instance, field)
                self.assertGreater(now, then)

    def test_load_tracking(self):
        call_command('filemaker_update', 'isisdata/tests/data', 'citation')
        call_command('filemaker_update', 'isisdata/tests/data', 'authority')
        call_command('filemaker_update', 'isisdata/tests/data', 'tracking')

        self.assertEqual(Tracking.objects.count(), 2)

        for instance in Tracking.objects.all():
            self.assertGreater(len(instance.notes), 0)
            self.assertGreater(len(instance.tracking_info), 0)
            self.assertTrue(instance.type_controlled is not None)

    def test_load_ac_relations(self):
        call_command('filemaker_update', 'isisdata/tests/data', 'citation')
        call_command('filemaker_update', 'isisdata/tests/data', 'authority')
        call_command('filemaker_update', 'isisdata/tests/data', 'acrelation')

        self.assertEqual(ACRelation.objects.count(), 2)

        for instance in ACRelation.objects.all():
            self.assertTrue(instance.citation is not None)
            self.assertTrue(instance.authority is not None)
            self.assertTrue(instance.description is not None)
            self.assertTrue(instance.type_controlled is not None)
            self.assertTrue(instance.type_broad_controlled is not None)
            self.assertTrue(instance.type_free is not None)
            self.assertGreater(instance.confidence_measure, 0)
            self.assertGreater(instance.relationship_weight, 0)
            for field in CURATION_FIELDS:
                self.assertGreater(len(getattr(instance, field)), 0)
            for field in DATETIME_FIELDS:
                now = UTC.localize(datetime.datetime.now())
                then = getattr(instance, field)
                self.assertGreater(now, then)

    def test_load_cc_relations(self):
        call_command('filemaker_update', 'isisdata/tests/data', 'citation')
        call_command('filemaker_update', 'isisdata/tests/data', 'authority')
        call_command('filemaker_update', 'isisdata/tests/data', 'ccrelation')

        self.assertEqual(CCRelation.objects.count(), 2)

        for instance in CCRelation.objects.all():
            self.assertTrue(instance.subject is not None)
            self.assertTrue(instance.object is not None)
            self.assertTrue(instance.name is not None)
            self.assertTrue(instance.description is not None)
            self.assertTrue(instance.type_controlled is not None)
            self.assertTrue(instance.type_free is not None)
            for field in CURATION_FIELDS:
                self.assertGreater(len(getattr(instance, field)), 0)
            for field in DATETIME_FIELDS:
                now = UTC.localize(datetime.datetime.now())
                then = getattr(instance, field)
                self.assertGreater(now, then)


if __name__ == '__main__':
    unittest.main()
