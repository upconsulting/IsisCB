from __future__ import unicode_literals
import json
from django.conf import settings


def user(request):
    return {'user': request.user}


def social(request):
    return {'facebook_app_id': settings.FACEBOOK_APP_ID}


def google(request):
    return {'GOOGLE_ANALYTICS_ID': settings.GOOGLE_ANALYTICS_ID}

def portal_prefix(request):
    print("prefix", settings.PORTAL_PREFIX)
    return {'PORTAL_PREFIX': settings.PORTAL_PREFIX}
