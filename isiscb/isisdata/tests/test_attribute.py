import unittest
from isisdata.models import Attribute
from django.contrib.auth.models import User
import datetime

class TestAttributeValue(unittest.TestCase):
    """
    Attribute.value can be an instance of just about anything.
    """

    def setUp(self):
        self.user = User.objects.get_or_create(
            username = 'test',
        )[0]

    def test_pickle_string(self):
        instance = Attribute(
            id='testattribute1',
            value = 'string',
            type_controlled = 'test',
            created_by=self.user,
            modified_by=self.user
        )
        instance.save()

        loaded_instance = Attribute.objects.get(id='testattribute1')

        self.assertIsInstance(loaded_instance.value, str)

        query = Attribute.objects.filter(value='string')
        self.assertEqual(query.count(), 1)

    def test_pickle_int(self):
        instance = Attribute(
            id='testattribute1',
            value = 1,
            type_controlled = 'test',
            created_by=self.user,
            modified_by=self.user
        )
        instance.save()

        loaded_instance = Attribute.objects.get(id='testattribute1')

        self.assertIsInstance(loaded_instance.value, int)
        query = Attribute.objects.filter(value=1)
        self.assertEqual(query.count(), 1)

    def test_pickle_float(self):
        instance = Attribute(
            id='testattribute1',
            value = 2.2,
            type_controlled = 'test',
            created_by=self.user,
            modified_by=self.user
        )
        instance.save()

        loaded_instance = Attribute.objects.get(id='testattribute1')

        self.assertIsInstance(loaded_instance.value, float)
        query = Attribute.objects.filter(value=2.2)
        self.assertEqual(query.count(), 1)

    def test_pickle_list(self):
        instance = Attribute(
            id='testattribute1',
            value = ['list', 1, 2.2],
            type_controlled = 'test',
            created_by=self.user,
            modified_by=self.user
        )
        instance.save()
        loaded_instance = Attribute.objects.get(id='testattribute1')

        self.assertIsInstance(loaded_instance.value, list)
        query = Attribute.objects.filter(value=['list', 1, 2.2])
        self.assertEqual(query.count(), 1)

    def test_pickle_datetime(self):
        now = datetime.datetime.now()
        instance = Attribute(
            id='testattribute1',
            value = now,
            type_controlled = 'test',
            created_by=self.user,
            modified_by=self.user
        )
        instance.save()

        loaded_instance = Attribute.objects.get(id='testattribute1')
        self.assertIsInstance(loaded_instance.value, datetime.datetime)

        query = Attribute.objects.filter(value=now)
        self.assertEqual(query.count(), 1)

        query = Attribute.objects.filter(value=datetime.datetime.now())
        self.assertEqual(query.count(), 0)


if __name__ == '__main__':
    unittest.main()
