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

sys.path.append('..')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '4z1u)a6b5l%#uf3qi$$$^s^3_*%cruf9pfk$jdgm&n2%ov11%m'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

MIGRATION_MODULES = {
    'isisdata': 'isisdata.migrations'
}

# Application definition

INSTALLED_APPS = (
    'autocomplete_light',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'social.apps.django_app.default',
    'rest_framework',
    'simple_history',
    'isisdata',
    'storages',
    'haystack',
    "elasticstack",
    'oauth2_provider',
    'captcha',
    'corsheaders',
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
)

AUTHENTICATION_BACKENDS = (
    'social.backends.twitter.TwitterOAuth',
    'social.backends.facebook.FacebookOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'social.apps.django_app.context_processors.backends',
    'social.apps.django_app.context_processors.login_redirect',
)


ROOT_URLCONF = 'isiscb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'isisdata.context_processors.social',
            ],
        },
    },
]

WSGI_APPLICATION = 'isiscb.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

# from secrets import POSTGRESQL_PASSWORD

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'isiscb',
        'USER': 'upconsulting',
        'PASSWORD': os.environ['RDS_PASSWORD'],
        'HOST': 'isiscb-develop-db-alt.cjicxluc6l0j.us-west-2.rds.amazonaws.com',
        'PORT': '5432',
    }
}

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'elasticstack.backends.ConfigurableElasticSearchEngine',
        'URL': 'ec2-54-69-38-140.us-west-2.compute.amazonaws.com:9200/',
        'INDEX_NAME': 'haystack',
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
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_METADATA_CLASS': 'isisdata.metadata.CCMetadata'
}


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/


# # secrets.py should set the AWS_SECRET_ACCESS_KEY
# from secrets import AWS_SECRET_ACCESS_KEY
AWS_STORAGE_BUCKET_NAME = 'isiscb-develop-staticfiles'
AWS_MEDIA_BUCKET_NAME = 'isiscb-develop-media'
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY']
AWS_S3_CUSTOM_DOMAIN = 's3.amazonaws.com'
AWS_S3_SECURE_URLS = False
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']

STATICFILES_DIRS = ['isisdata/static']
STATICFILES_LOCATION = '%s/static' % AWS_STORAGE_BUCKET_NAME
STATICFILES_STORAGE = 'custom_storages.StaticStorage'
STATIC_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, STATICFILES_LOCATION)

MEDIAFILES_LOCATION = '%s/media' % AWS_MEDIA_BUCKET_NAME
MEDIA_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, MEDIAFILES_LOCATION)
DEFAULT_FILE_STORAGE = 'custom_storages.MediaStorage'

AWS_HEADERS = {
    'Expires': 'Thu, 31 Dec 2099 20:00:00 GMT',
    'Cache-Control': 'max-age=94608000',
}

DOMAIN = 'isiscb-develop.aplacecalledup.com'
URI_PREFIX = 'http://isiscb-develop.aplacecalledup.com/isis/'
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

# try:
#     from secrets import SMTP_USER, SMTP_PASSWORD
#     EMAIL_HOST_USER = SMTP_USER
#     EMAIL_HOST_PASSWORD = SMTP_PASSWORD
# except ImportError:
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD =''
EMAIL_HOST = 'email-smtp.us-west-2.amazonaws.com'
SMTP_EMAIL = 'info@aplacecalledup.com'

CAPTCHA_CHALLENGE_FUNCT = 'captcha.helpers.math_challenge'


# social

FACEBOOK_APP_ID = '1694252594140628'
SOCIAL_AUTH_FACEBOOK_KEY = FACEBOOK_APP_ID
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email']

SOCIAL_AUTH_TWITTER_KEY = 'Vz6Nq70ijJYb2IOSLzetQVwJR'

# try:
#     from secrets import SOCIAL_AUTH_FACEBOOK_SECRET, SOCIAL_AUTH_TWITTER_SECRET
# except ImportError:
SOCIAL_AUTH_TWITTER_SECRET = ''
SOCIAL_AUTH_FACEBOOK_SECRET = ''


LICENSE = """This work is licensed under a Creative Commons
             Attribution-NonCommercial 4.0 International License."""
