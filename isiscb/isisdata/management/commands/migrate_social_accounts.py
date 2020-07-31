from django.core.management.base import BaseCommand, CommandError
from allauth.socialaccount.models import SocialAccount
from django.db import models

class Command(BaseCommand):
    help = 'Migrate existing social auth accounts to allauth.'

    def handle(self, *args, **options):
        accounts = UserSocialAuth.objects.all()
        for account in accounts:
            social_account = SocialAccount()
            social_account.user_id = account.user_id
            social_account.provider = account.provider
            social_account.uid = account.uid
            social_account.save()



USER_MODEL = 'auth.User'
UID_LENGTH = 255

class JSONField(models.TextField):
    """Simple JSON field that stores python structures as JSON strings
    on database.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', dict)
        super(JSONField, self).__init__(*args, **kwargs)

    def from_db_value(self, value, *args, **kwargs):
        return self.to_python(value)

    def to_python(self, value):
        """
        Convert the input JSON value into python structures, raises
        django.core.exceptions.ValidationError if the data can't be converted.
        """
        if self.blank and not value:
            return {}
        value = value or '{}'
        return value

    def validate(self, value, model_instance):
        """Check value is a valid JSON string, raise ValidationError on
        error."""
        if isinstance(value, six.string_types):
            super(JSONField, self).validate(value, model_instance)
            try:
                json.loads(value)
            except Exception as err:
                raise ValidationError(str(err))

    def get_prep_value(self, value):
        """Convert value to JSON string before save"""
        try:
            return json.dumps(value)
        except Exception as err:
            raise ValidationError(str(err))

    def value_to_string(self, obj):
        """Return value from object converted to string properly"""
        return force_text(self.value_from_object(obj))

    def value_from_object(self, obj):
        """Return value dumped to string."""
        orig_val = super(JSONField, self).value_from_object(obj)
        return self.get_prep_value(orig_val)

class AbstractUserSocialAuth(models.Model):
    """Abstract Social Auth association model"""
    user = models.ForeignKey(USER_MODEL, related_name='social_auth',
                             on_delete=models.CASCADE)
    provider = models.CharField(max_length=32)
    uid = models.CharField(max_length=UID_LENGTH, db_index=True)
    extra_data = JSONField()

    def __str__(self):
        return str(self.user)

    class Meta:
        app_label = "social_django"
        abstract = True



class UserSocialAuth(AbstractUserSocialAuth):
    """Social Auth association model"""

    class Meta:
        """Meta data"""
        app_label = "social_django"
        unique_together = ('provider', 'uid')
        db_table = 'social_auth_usersocialauth'
