"""
Django settings for isiscb project.

Generated by 'django-admin startproject' using Django 1.8.3.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""
from __future__ import unicode_literals

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import sys
import markdown

sys.path.append('..')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

DEBUG = eval(os.environ.get('DEBUG', 'False'))

ALLOWED_HOSTS = ['*']

MIGRATION_MODULES = {
    'isisdata': 'isisdata.migrations'
}

# Application definition

INSTALLED_APPS = (
    'dal',
    'dal_select2',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.twitter',
    'rest_framework',
    'simple_history',
    'isisdata',
    #'storages',
    'haystack',
    "elasticstack",
    'oauth2_provider',
    'captcha',
    'corsheaders',
    'zotero',
    'openurl',
    'curation',
    'rules.apps.AutodiscoverRulesConfig',
    'django_celery_results',
)

CORS_ORIGIN_ALLOW_ALL = True

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    # 'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.cache.FetchFromCacheMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    #'dj_pagination.middleware.PaginationMiddleware',
)

LOGGING = {
	"version": 1,
	"disable_existing_loggers": False,
	"formatters": {
		"verbose": {"format": "%(asctime)s %(levelname)s %(module)s: %(message)s"}
	},
	"handlers": {
		"app_analyzer": {
			"level": "DEBUG",
			"class": "logging.FileHandler",
			"filename": "/var/log/app_analyzer.log",
			"formatter": "verbose",
		}
	},
	"loggers": {
		"app_analyzer": {"handlers": ["app_analyzer"], "level": "DEBUG", "propagate": True}
	},
}

# TEMPLATE_CONTEXT_PROCESSORS = (
#     'social.apps.django_app.context_processors.backends',
#     'social.apps.django_app.context_processors.login_redirect',
#     'isisdata.context_processors.user',
#     'isisdata.context_processors.social',
#     'isisdata.context_processors.google',
# )


ROOT_URLCONF = 'isiscb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['isisdata/templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                'isisdata.context_processors.social',
                'isisdata.context_processors.google',
            ],
        },
    },
]

WSGI_APPLICATION = 'isiscb.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get('RDS_DB_NAME', ''),
        'USER': os.environ.get('RDS_USERNAME', ''),
        'PASSWORD': os.environ.get('RDS_PASSWORD', ''),
        'HOST': os.environ.get('RDS_HOSTNAME', ''),
        'PORT': os.environ.get('RDS_PORT', ''),
    }
}

ELASTICSEARCH_HOST = os.environ.get('ELASTICSEARCH_HOST', '')
ELASTICSEARCH_INDEX = os.environ.get('ELASTICSEARCH_INDEX', '')

HAYSTACK_DEFAULT_INDEX = 'default'

HAYSTACK_CONNECTIONS = {
    HAYSTACK_DEFAULT_INDEX: {
        'ENGINE': 'isisdata.elasticsearch_backend.IsisCBElasticsearchSearchEngine',
        # 'ENGINE': 'elasticstack.backends.ConfigurableElasticSearchEngine',
        'URL': ELASTICSEARCH_HOST,
        'INDEX_NAME': ELASTICSEARCH_INDEX,
    },
}

ELASTICSEARCH_INDEX_SETTINGS = {
     "settings" : {
         "analysis" : {
             "analyzer" : {
                 "default" : {
                     "tokenizer" : "standard",
                     "filter" : ["standard", "asciifolding"]
                 }
             }
         }
     }
 }


ELASTICSEARCH_DEFAULT_ANALYZER = 'default'

CACHES = {
    #'default': {
    #    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    #    'LOCATION': 'unique-snowflake',
    #},
    'default': {
        'BACKEND': "django.core.cache.backends.db.DatabaseCache",
        'LOCATION': 'db_cache_snowflake',
    },
    'search_results_cache': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'search_cache',
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

OAUTH2_PROVIDER = {
    'SCOPES': {'read': 'Read scope', 'api': 'API scope'}
}

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_METADATA_CLASS': 'isisdata.metadata.CCMetadata'
}

SOCIAL_AUTH_TWITTER_KEY = os.environ.get('SOCIAL_AUTH_TWITTER_KEY', '')
SOCIAL_AUTH_TWITTER_SECRET = os.environ.get('SOCIAL_AUTH_TWITTER_SECRET', '')

SOCIAL_AUTH_FACEBOOK_KEY = os.environ.get('SOCIAL_AUTH_FACEBOOK_KEY', '')
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email']
SOCIAL_AUTH_FACEBOOK_SECRET = os.environ.get('SOCIAL_AUTH_FACEBOOK_SECRET', '')

SOCIALACCOUNT_PROVIDERS = {
    'twitter': {
        # For each OAuth based provider, either add a ``SocialApp``
        # (``socialaccount`` app) containing the required client
        # credentials, or list them here:
        'APP': {
            'client_id': SOCIAL_AUTH_TWITTER_KEY,
            'secret': SOCIAL_AUTH_TWITTER_SECRET,
            'key': ''
        }
    },
    'facebook': {
        # For each OAuth based provider, either add a ``SocialApp``
        # (``socialaccount`` app) containing the required client
        # credentials, or list them here:
        'APP': {
            'client_id': SOCIAL_AUTH_FACEBOOK_KEY,
            'secret': SOCIAL_AUTH_FACEBOOK_SECRET,
            'key': ''
        },
        'METHOD': 'oauth2',
        'fields': SOCIAL_AUTH_FACEBOOK_SCOPE
    }
}

SOCIALACCOUNT_AUTO_SIGNUP = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
AWS_MEDIA_BUCKET_NAME = os.environ.get('AWS_MEDIA_BUCKET_NAME', '')
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY', '')
AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
AWS_S3_SECURE_URLS = True
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

STATICFILES_DIRS = ['isisdata/static', 'curation/static']
STATICFILES_LOCATION = ''#% AWS_STORAGE_BUCKET_NAME
# STATICFILES_STORAGE = 'custom_storages.StaticStorage'
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

STATIC_URL = "https://%s.s3.amazonaws.com/%s" % (AWS_STORAGE_BUCKET_NAME, STATICFILES_LOCATION)
# STATIC_URL ='/static/'

MEDIA_URL = '/media/'

MEDIAFILES_LOCATION = '%s/media' % AWS_MEDIA_BUCKET_NAME
MEDIA_URL = "https://%s.s3.amazonaws.com/%s/" % (AWS_MEDIA_BUCKET_NAME, STATICFILES_LOCATION)
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

SITE_ID = 1

AWS_EXPORT_BUCKET_NAME = os.environ.get('AWS_EXPORT_BUCKET_NAME')
AWS_IMPORT_BUCKET_NAME = os.environ.get('AWS_IMPORT_BUCKET_NAME')

AWS_S3_OBJECT_PARAMETERS = {
    'Expires': 'Thu, 31 Dec 2099 20:00:00 GMT',
    'CacheControl': 'max-age=94608000',
}

S3_UPLOAD_BULK_CHANGE_PATH = 's3://{}:{}@{}/'.format(AWS_ACCESS_KEY_ID,
                                AWS_SECRET_ACCESS_KEY,
                                AWS_EXPORT_BUCKET_NAME)

UPLOAD_BULK_CHANGE_PATH = os.environ.get('UPLOAD_BULK_CHANGE_PATH', S3_UPLOAD_BULK_CHANGE_PATH)

S3_BULK_CHANGE_ERROR_PATH = 's3://{}:{}@{}/'.format(AWS_ACCESS_KEY_ID,
                                AWS_SECRET_ACCESS_KEY,
                                AWS_EXPORT_BUCKET_NAME)

BULK_CHANGE_ERROR_PATH = os.environ.get('BULK_CHANGE_ERROR_PATH', S3_BULK_CHANGE_ERROR_PATH)


S3_IMPORT_PATH = 's3://%s:%s@%s/' % (AWS_ACCESS_KEY_ID,
                                AWS_SECRET_ACCESS_KEY,
                                AWS_EXPORT_BUCKET_NAME)
UPLOAD_IMPORT_PATH = os.environ.get('UPLOAD_IMPORT_PATH', S3_IMPORT_PATH)

DOMAIN = os.environ.get('DJANGO_DOMAIN','')
URI_PREFIX = os.environ.get('DJANGO_URI_PREFIX', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', True)
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', False)

EMAIL_HOST_USER = os.environ.get('SMTP_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
EMAIL_HOST = os.environ.get('SMTP_HOST', '')
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', '')
DEFAULT_FROM_EMAIL = os.environ.get('SMTP_EMAIL', '')

CAPTCHA_CHALLENGE_FUNCT = 'captcha.helpers.math_challenge'
CAPTCHA_FONT_SIZE = 36

ACCOUNT_FORMS = {'signup': 'isisdata.forms.UserRegistrationForm'}

FACEBOOK_APP_ID = SOCIAL_AUTH_FACEBOOK_KEY
FACEBOOK_API_SECRET = SOCIAL_AUTH_FACEBOOK_SECRET

GOOGLE_ANALYTICS_ID = os.environ.get('GOOGLE_ANALYTICS_ID', '')


LICENSE = """This work is licensed under a Creative Commons Attribution-NonCommercial 4.0 International License."""


MARKUP_FIELD_TYPES = (
    ('markdown', markdown.markdown),
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'


CELERY_RESULT_BACKEND = 'django-cache'

# If you want to use Redis for Celery message passing, uncomment these options
#  and comment out the SQS options, below.
# CELERY_REDIS_HOST = 'redis://'
# CELERY_BROKER_URL = 'redis://'

# The following configuration options are used for Amazon SQS message passing.
CELERY_TASK_TRACK_STARTED = True
CELERY_IMPORTS = ('curation.tasks',)

CELERY_BROKER_TRANSPORT = 'sqs'
SQS_REGION = os.environ.get('SQS_REGION', 'sqs.us-west-2')
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'region': SQS_REGION,
    #'queue_name_prefix': os.environ.get('SQS_QUEUE_PREFIX', 'isiscb-staging-messages') + '-'
}
BROKER_TRANSPORT_OPTIONS = {
    'region': SQS_REGION,
    #'queue_name_prefix': os.environ.get('SQS_QUEUE_PREFIX', 'isiscb-staging-messages') + '-'
}
#CELERY_BROKER_USER = AWS_ACCESS_KEY_ID
#CELERY_BROKER_PASSWORD = AWS_SECRET_ACCESS_KEY

CELERY_BROKER_URL = 'sqs://'
CELERY_DEFAULT_QUEUE = os.environ.get('SQS_QUEUE', 'isiscb-staging-messages')
CELERY_GRAPH_TASK_QUEUE = os.environ.get('SQS_QUEUE_GRAPHS', 'isiscb-staging-graphs-messages')
CELERY_QUEUES = {
    CELERY_DEFAULT_QUEUE: {
        'exchange': CELERY_DEFAULT_QUEUE,
        'binding_key': CELERY_DEFAULT_QUEUE,
    },
    CELERY_GRAPH_TASK_QUEUE: {
        'exchange': CELERY_GRAPH_TASK_QUEUE,
        'binding_key': CELERY_GRAPH_TASK_QUEUE,
    }
}
CELERY_TASK_DEFAULT_QUEUE = CELERY_DEFAULT_QUEUE
CELERY_WORKER_PREFETCH_MULTIPLIER=0
CELERY_BROKER_CONNECTION_RETRY=False

LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/'

ACCOUNT_FORMS = {'signup': 'isisdata.forms.UserRegistrationForm'}
ACCOUNT_EMAIL_REQUIRED = True

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
    'social_core.pipeline.social_auth.associate_by_email',
)

CITATION_CREATION_DEFAULT_DATE = "2000-01-01T00:00:00Z"

# time till next timeline refresh in hours (720 = 30 days)
AUTHORITY_TIMELINE_REFRESH_TIME = os.environ.get('AUTHORITY_TIMELINE_REFRESH_TIME', 720)
AUTHORITY_TIMELINE_REFRESH_TIME_USER_INIT = os.environ.get('AUTHORITY_TIMELINE_REFRESH_TIME_USER_INIT', 0.25)

TIMELINE_PUBLICATION_DATE_ATTRIBUTE = os.environ.get('TIMELINE_PUBLICATION_DATE_ATTRIBUTE', "PublicationDate")
RECORD_SUBTYPE_ATTRIBUTE = os.environ.get('RECORD_SUBTYPE_ATTRIBUTE', "RecordSubType")
ACCESSED_ATTRIBUTE_NAME = os.environ.get('ACCESSED_ATTRIBUTE_NAME', "LastAccessedDate")
BIBLIOGRAPHIC_ESSAY_ATTRIBUTE_NAME = os.environ.get('BIBLIOGRAPHIC_ESSAY_ATTRIBUTE_NAME', "BibliographicEssay")

COUNTRY_CODE_ATTRIBUTE = os.environ.get('COUNTRY_CODE_ATTRIBUTE', "CountryCode")

DOI_LINKED_DATA_NAME = os.environ.get('DOI_LINKED_DATA_NAME', "DOI")
ISBN_LINKED_DATA_NAME = os.environ.get('ISBN_LINKED_DATA_NAME', "ISBN")
URL_LINKED_DATA_NAME = os.environ.get('URL_LINKED_DATA_NAME', "URL")

JOURNAL_ABBREVIATION_ATTRIBUTE_NAME = os.environ.get('JOURNAL_ABBREVIATION_ATTRIBUTE_NAME', "JournalAbbr")
PERSON_BIRTH_DATE_ATTRIBUTE = os.environ.get('PERSON_BIRTH_DATE_ATTRIBUTE', "Birth date")
PERSON_DEATH_DATE_ATTRIBUTE = os.environ.get('PERSON_BIRTH_DATE_ATTRIBUTE', "Death date")
PERSON_BIRTH_DEATH_DATE_ATTRIBUTE = os.environ.get('PERSON_BIRTH_DATE_ATTRIBUTE', "BirthToDeathDates")

DATASET_ISISCB_NAME_PREFIX = os.environ.get('DATASET_ISISCB_NAME_PREFIX', 'Isis Bibliography of the History of Science')
DATASET_ISISCB_NAME_DISPLAY = os.environ.get('DATASET_ISISCB_NAME_DISPLAY', 'Isis Bibliography of the History of Science')
DATASET_SHOT_NAME_PREFIX = os.environ.get('DATASET_SHOT_NAME_PREFIX', 'Technology & Culture Bibliography')
DATASET_SHOT_NAME_DISPLAY = os.environ.get('DATASET_SHOT_NAME_DISPLAY', 'Technology & Culture Bibliography')
