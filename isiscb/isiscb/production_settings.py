"""
Django settings for isiscb project.

Generated by 'django-admin startproject' using Django 1.8.3.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

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
    'autocomplete_light',
    'isisdata',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'social_django',
    'pagination',
    'rest_framework',
    'markupfield',
    'simple_history',
    'storages',
    'haystack',
    'captcha',
    "elasticstack",     # TODO: Do we need this?
    'oauth2_provider',
    'corsheaders',
    'zotero',
    'openurl',
    'curation',
    'rules',
    'django_celery_results',
)

CORS_ORIGIN_ALLOW_ALL = True

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'pagination.middleware.PaginationMiddleware',
)



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
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
                'isisdata.context_processors.social',
                'isisdata.context_processors.google',
                 'django.template.context_processors.tz',
                 'isisdata.context_processors.user',
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

HAYSTACK_CONNECTIONS = {
    'default': {
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
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
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
        'oauth2_provider.ext.rest_framework.OAuth2Authentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_METADATA_CLASS': 'isisdata.metadata.CCMetadata',
    'EXCEPTION_HANDLER': 'isisdata.exceptions.custom_exception_handler'
}

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
STATICFILES_STORAGE = 'storages.backends.s3boto.S3BotoStorage'

STATIC_URL = "https://%s.s3.amazonaws.com/%s" % (AWS_STORAGE_BUCKET_NAME, STATICFILES_LOCATION)
# STATIC_URL ='/static/'

MEDIA_URL = '/media/'

MEDIAFILES_LOCATION = '%s/media' % AWS_MEDIA_BUCKET_NAME
MEDIA_URL = "https://%s.s3.amazonaws.com/%s/" % (AWS_MEDIA_BUCKET_NAME, STATICFILES_LOCATION)
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'

AWS_EXPORT_BUCKET_NAME = os.environ.get('AWS_EXPORT_BUCKET_NAME')

AWS_HEADERS = {
    'Expires': 'Thu, 31 Dec 2099 20:00:00 GMT',
    'Cache-Control': 'max-age=94608000',
}

DOMAIN = os.environ.get('DJANGO_DOMAIN','')
URI_PREFIX = os.environ.get('DJANGO_URI_PREFIX', '')
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

EMAIL_HOST_USER = os.environ.get('SMTP_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
EMAIL_HOST = os.environ.get('SMTP_HOST', '')
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', '')

CAPTCHA_CHALLENGE_FUNCT = 'captcha.helpers.math_challenge'
CAPTCHA_FONT_SIZE = 36

SOCIAL_AUTH_FACEBOOK_KEY = os.environ.get('SOCIAL_AUTH_FACEBOOK_KEY', '')
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email']

SOCIAL_AUTH_TWITTER_KEY = os.environ.get('SOCIAL_AUTH_TWITTER_KEY','')
SOCIAL_AUTH_FACEBOOK_SECRET = os.environ.get('SOCIAL_AUTH_FACEBOOK_SECRET', '')
SOCIAL_AUTH_TWITTER_SECRET = os.environ.get('SOCIAL_AUTH_TWITTER_SECRET', '')

TWITTER_CONSUMER_KEY = SOCIAL_AUTH_TWITTER_KEY
TWITTER_CONSUMER_SECRET = SOCIAL_AUTH_TWITTER_SECRET
FACEBOOK_APP_ID = SOCIAL_AUTH_FACEBOOK_KEY
FACEBOOK_API_SECRET = SOCIAL_AUTH_FACEBOOK_SECRET

GOOGLE_ANALYTICS_ID = os.environ.get('GOOGLE_ANALYTICS_ID', '')


LICENSE = """This work is licensed under a Creative Commons Attribution-NonCommercial 4.0 International License."""


MARKUP_FIELD_TYPES = (
    ('markdown', markdown.markdown),
)

AUTHENTICATION_BACKENDS = (
    'social_core.backends.twitter.TwitterOAuth',
    'social_core.backends.facebook.FacebookOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'


CELERY_RESULT_BACKEND = 'django-cache'#'django-cache'

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
    'queue_name_prefix': os.environ.get('SQS_QUEUE', 'isiscb-staging-messages') + '-'
}
BROKER_TRANSPORT_OPTIONS = {
    'region': SQS_REGION,
    'queue_name_prefix': os.environ.get('SQS_QUEUE', 'isiscb-staging-messages') + '-'
}
CELERY_BROKER_USER = AWS_ACCESS_KEY_ID
CELERY_BROKER_PASSWORD = AWS_SECRET_ACCESS_KEY
CELERY_DEFAULT_QUEUE = os.environ.get('SQS_QUEUE', 'isiscb-staging-messages')
CELERY_QUEUES = {
    CELERY_DEFAULT_QUEUE: {
        'exchange': CELERY_DEFAULT_QUEUE,
        'binding_key': CELERY_DEFAULT_QUEUE,
    }
}
CELERY_TASK_DEFAULT_QUEUE = CELERY_DEFAULT_QUEUE
CELERY_WORKER_PREFETCH_MULTIPLIER=1

LOGIN_REDIRECT_URL = '/'


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
