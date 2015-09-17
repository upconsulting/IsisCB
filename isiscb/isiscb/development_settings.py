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
    'rest_framework',
    'simple_history',
    'isisdata',
    'storages',
    'haystack',
    'captcha',

)

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
                'isisdata.context_processors.server_start',
            ],
        },
    },
]

WSGI_APPLICATION = 'isiscb.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

from secrets import POSTGRESQL_PASSWORD

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'isiscb',
        'USER': 'upconsulting',
        'PASSWORD': POSTGRESQL_PASSWORD,
        'HOST': 'isiscb-develop-db-alt.cjicxluc6l0j.us-west-2.rds.amazonaws.com',
        'PORT': '5432',
    }
}

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
        'URL': 'ec2-52-89-8-78.us-west-2.compute.amazonaws.com:9200/',
        'INDEX_NAME': 'haystack',
    },
}


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 10
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/


# secrets.py should set the AWS_SECRET_ACCESS_KEY
from secrets import AWS_SECRET_ACCESS_KEY

AWS_STORAGE_BUCKET_NAME = 'isiscb-develop-staticfiles'
AWS_MEDIA_BUCKET_NAME = 'isiscb-develop-media'
AWS_ACCESS_KEY_ID = 'AKIAIL2MMPDWFF576XUQ'
AWS_S3_CUSTOM_DOMAIN = 's3.amazonaws.com'
AWS_S3_SECURE_URLS = False

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

from secrets import SMTP_USER, SMTP_PASSWORD
EMAIL_HOST = 'email-smtp.us-west-2.amazonaws.com'
EMAIL_HOST_USER = SMTP_USER
EMAIL_HOST_PASSWORD = SMTP_PASSWORD
SMTP_EMAIL = 'info@aplacecalledup.com'
