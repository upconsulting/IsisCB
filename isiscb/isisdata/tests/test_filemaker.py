from django.core.management import call_command

import unittest
import os
import datetime
import pytz

from isisdata.models import *

DATETIME_FIELDS = [
    'created_on_fm',
]

CURATION_FIELDS = [
    'administrator_notes',
    'record_history',
    'created_by_fm',
]

UTC = pytz.UTC

class TestLoadFileMaker(unittest.TestCase):

    def test_load_authorities(self):
        call_command('loaddata', 'language.json')
        call_command('filemaker', 'isisdata/tests/data', 'authorities')

        self.assertEqual(Authority.objects.count(), 3)
        for instance in Authority.objects.all():
            self.assertGreater(len(instance.name), 0)
            self.assertGreater(len(instance.description), 0)
            self.assertGreater(len(instance.classification_system), 0)
            self.assertGreater(len(instance.classification_code), 0)
            self.assertGreater(len(instance.classification_hierarchy), 0)
            self.assertGreater(len(instance.record_status), 0)
            self.assertGreater(len(instance.classification_system), 0)
            for field in CURATION_FIELDS:
                self.assertGreater(len(getattr(instance, field)), 0)
            for field in DATETIME_FIELDS:
                now = UTC.localize(datetime.datetime.now())
                then = getattr(instance, field)
                self.assertGreater(now, then)

            if instance.record_status == 'RD':
                self.assertTrue(instance.redirect_to is not None)

    def test_load_citations(self):
        call_command('filemaker', 'isisdata/tests/data', 'citations')

        self.assertEqual(Citation.objects.count(), 2)

        for instance in Citation.objects.all():
            self.assertGreater(len(instance.title), 0)
            self.assertGreater(len(instance.description), 0)
            self.assertGreater(len(instance.type_controlled), 0)
            self.assertGreater(len(instance.abstract), 0)
            self.assertGreater(len(instance.edition_details), 0)
            self.assertGreater(len(instance.physical_details), 0)
            self.assertGreater(len(instance.record_action), 0)
            self.assertGreater(len(instance.status_of_record), 0)
            self.assertGreater(instance.language.count(), 0)
            for field in CURATION_FIELDS:
                self.assertGreater(len(getattr(instance, field)), 0)
            for field in DATETIME_FIELDS:
                now = UTC.localize(datetime.datetime.now())
                then = getattr(instance, field)
                self.assertGreater(now, then)

    def test_load_attributes(self):
        call_command('filemaker', 'isisdata/tests/data', 'citations')
        call_command('filemaker', 'isisdata/tests/data', 'authorities')
        call_command('filemaker', 'isisdata/tests/data', 'attributes')

        self.assertEqual(Attribute.objects.count(), 1)
        self.assertEqual(Value.objects.count(), 1)

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
        call_command('loaddata', 'linkeddatatypes.json')
        call_command('filemaker', 'isisdata/tests/data', 'citations')
        call_command('filemaker', 'isisdata/tests/data', 'authorities')
        call_command('filemaker', 'isisdata/tests/data', 'linkeddata')

        self.assertEqual(LinkedData.objects.count(), 2)

        for instance in LinkedData.objects.all():
            self.assertTrue(instance.universal_resource_name is not None)
            self.assertTrue(instance.type_controlled is not None)
            for field in CURATION_FIELDS:
                self.assertGreater(len(getattr(instance, field)), 0)
            for field in DATETIME_FIELDS:
                now = UTC.localize(datetime.datetime.now())
                then = getattr(instance, field)
                self.assertGreater(now, then)

    def test_load_tracking(self):
        call_command('filemaker', 'isisdata/tests/data', 'citations')
        call_command('filemaker', 'isisdata/tests/data', 'authorities')
        call_command('filemaker', 'isisdata/tests/data', 'tracking')

        self.assertEqual(Tracking.objects.count(), 2)

        for instance in Tracking.objects.all():
            self.assertGreater(len(instance.notes), 0)
            self.assertGreater(len(instance.tracking_info), 0)
            self.assertTrue(instance.type_controlled is not None)

    def test_load_ac_relations(self):
        call_command('filemaker', 'isisdata/tests/data', 'citations')
        call_command('filemaker', 'isisdata/tests/data', 'authorities')
        call_command('filemaker', 'isisdata/tests/data', 'ac_relations')

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
        call_command('filemaker', 'isisdata/tests/data', 'citations')
        call_command('filemaker', 'isisdata/tests/data', 'authorities')
        call_command('filemaker', 'isisdata/tests/data', 'cc_relations')

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
