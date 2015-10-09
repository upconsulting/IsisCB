import json
from django.conf import settings

def server_start(request):
    """
    Add the datetime of last server start to the template context.
    """
    with open('server_start', 'r') as f:
        start_datetime = json.load(f)
    return {'server_start': start_datetime}

def social(request):
    return {'facebook_app_id': settings.FACEBOOK_APP_ID}
