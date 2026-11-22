from django.test import TestCase

from isisdata.models import Authority, AuthorityValue


class TestAuthorityValue(TestCase):
    def setUp(self):
        self.authority = Authority.objects.create(
            name='Test authority',
            id='CBA000000001',
            type_controlled=Authority.PERSON,
        )

    def test_string_id_resolves_when_initializing(self):
        value = AuthorityValue(value=self.authority.pk)

        self.assertEqual(value.value, self.authority)

    def test_string_id_resolves_when_assigning(self):
        value = AuthorityValue()
        value.value = self.authority.pk

        self.assertEqual(value.value, self.authority)

    def test_authority_instance_assignment_is_unchanged(self):
        value = AuthorityValue(value=self.authority)

        self.assertEqual(value.value, self.authority)
