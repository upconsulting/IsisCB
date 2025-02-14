from __future__ import unicode_literals
from django.conf import settings
from isisdata.models import SystemNotification


def user(request):
    return {'user': request.user}


def social(request):
    return {'facebook_app_id': settings.FACEBOOK_APP_ID}


def google(request):
    return {'GOOGLE_ANALYTICS_ID': settings.GOOGLE_ANALYTICS_ID}

def portal_prefix(request):
    return {'PORTAL_PREFIX': settings.PORTAL_PREFIX}

def notifications(request):
    active_messages = SystemNotification.objects.filter(active=True)
    if active_messages:
        return {'notifications': active_messages }
    return {}

def cache_timeout(request):
    return {'CACHE_TIMEOUT': settings.CACHE_TIMEOUT}