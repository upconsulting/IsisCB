import json
from django.conf import settings

def social(request):
    return {'facebook_app_id': settings.FACEBOOK_APP_ID}
