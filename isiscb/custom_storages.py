# custom_storages.py
from django.conf import settings
from storages.backends.s3boto import S3BotoStorage

class StaticStorage(S3BotoStorage):
	location = settings.STATICFILES_LOCATION
	bucket_name = ''

class MediaStorage(S3BotoStorage):
	location = settings.MEDIAFILES_LOCATION
	bucket_name = ''
