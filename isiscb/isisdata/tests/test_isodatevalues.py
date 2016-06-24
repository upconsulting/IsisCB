import unittest

from django.contrib.contenttypes.models import ContentType
from isisdata.models import ISODateValue, ISODateRangeValue, Attribute, AttributeType
import datetime


class TestISODateValue(unittest.TestCase):
    def setUp(self):
        value_type = ContentType.objects.get_for_model(ISODateValue)
        subject_type = ContentType.objects.get_for_model(AttributeType)

        self.attribute_type = AttributeType.objects.create(
            name='TestType',
            value_content_type=value_type
        )
        self.attribute = Attribute.objects.create(
            type_controlled=self.attribute_type,
            source_content_type=subject_type,
            source_instance_id=unicode(self.attribute_type.id)
        )

    def _do_test(self, date, precision):
        value = ISODateValue.objects.create(value=date, attribute=self.attribute)
        self.assertIsInstance(value.value, list)
        print value
        self.assertIsInstance(value.precision, unicode)
        self.assertEqual(value.precision, precision)
        return value.value

    def test_create_datevalue_from_date(self):
        value = self._do_test(datetime.date.today(), 'day')

    def test_create_datevalue_from_datetime(self):
        value = self._do_test(datetime.datetime.now(), 'day')

    def test_create_datevalue_from_str_full(self):
        value = self._do_test('1999-01-05', 'day')

    def test_create_datevalue_from_str_month(self):
        value = self._do_test('1999-01', 'month')

    def test_create_datevalue_from_str_year(self):
        value = self._do_test('1999', 'year')

    def test_create_datevalue_from_str_bc(self):
        value = self._do_test('-1999-01-05', 'day')
        self.assertLess(value[0], 0)

    def test_create_datevalue_from_str_bc_month(self):
        value = self._do_test('-1999-01', 'month')
        self.assertLess(value[0], 0)

    def test_create_datevalue_from_str_bc_year(self):
        value = self._do_test('-1999', 'year')
        self.assertLess(value[0], 0)

    def test_create_datevalue_from_list_full(self):
        value = self._do_test([1999, 01, 05], 'day')

    def test_create_datevalue_from_tuple_full(self):
        value = self._do_test((1999, 01, 05), 'day')

    def test_create_datevalue_from_int(self):
        value = self._do_test(1999, 'year')

    def test_create_datevalue_from_int_bc(self):
        value = self._do_test(-1999, 'year')
        self.assertLess(value[0], 0)


class TestISODateRangeValue(unittest.TestCase):
    def setUp(self):
        value_type = ContentType.objects.get_for_model(ISODateRangeValue)
        subject_type = ContentType.objects.get_for_model(AttributeType)

        self.attribute_type = AttributeType.objects.create(
            name='TestType',
            value_content_type=value_type
        )
        self.attribute = Attribute.objects.create(
            type_controlled=self.attribute_type,
            source_content_type=subject_type,
            source_instance_id=unicode(self.attribute_type.id)
        )

    def _do_test(self, date):
        value = ISODateRangeValue.objects.create(value=date, attribute=self.attribute)
        self.assertIsInstance(value.value, list)
        print value
        return value.value

    def test_create_daterangevalue_from_date(self):
        date = [datetime.date.today(), datetime.date.today()]
        value = self._do_test(date)

    def test_create_daterangevalue_from_datetime(self):
        date = [datetime.datetime.now(), datetime.datetime.now()]
        value = self._do_test(date)

    def test_create_daterangevalue_from_str_full(self):
        value = self._do_test(['1999-01-05', '1999-01-06'])

    def test_create_daterangevalue_from_str_month(self):
        value = self._do_test(['1999-01', '1999-02'])

    def test_create_daterangevalue_from_str_year(self):
        date = ['1999', '2000']
        value = self._do_test(date)

    def test_create_daterangevalue_from_str_bc(self):
        date = ['-1999-01-05', '-1999-01-04']
        value = self._do_test(date)
        self.assertLess(value[0][0], 0)

    def test_create_daterangevalue_from_str_bc_month(self):
        date = ['-1999-01', '-1998-01']
        value = self._do_test(date)
        self.assertLess(value[0][0], 0)

    def test_create_daterangevalue_from_str_bc_year(self):
        date = ['-1999', '-1998']
        value = self._do_test(date)
        self.assertLess(value[0][0], 0)

    def test_create_daterangevalue_from_list_full(self):
        date = [[1999, 01, 05], [1999, 01, 06]]
        value = self._do_test(date)

    def test_create_daterangevalue_from_tuple_full(self):
        date = [(1999, 01, 05), (1999, 01, 06)]
        value = self._do_test(date)

    def test_create_daterangevalue_from_int(self):
        date = [1999, 2000]
        value = self._do_test(date)

    def test_create_daterangevalue_from_int_bc(self):
        date = [-1999, -1998]
        value = self._do_test(date)
        self.assertLess(value[0][0], 0)
