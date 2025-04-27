from storages.backends.s3boto3 import S3Boto3Storage

class StaticStorage(S3Boto3Storage):
    location = 'static'
    default_acl = 'public-read'

# we need to stay backwards compatible, and before media files would be stored in static
class MediaStorage(S3Boto3Storage):
    location = 'static'
    file_overwrite = False