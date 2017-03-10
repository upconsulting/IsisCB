import json
from django.conf import settings

def social(request):
    return {'facebook_app_id': settings.FACEBOOK_APP_ID}

def google(request):
    return {'GOOGLE_ANALYTICS_ID': settings.GOOGLE_ANALYTICS_ID}
