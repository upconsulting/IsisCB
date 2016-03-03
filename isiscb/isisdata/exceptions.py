from django.conf import settings
from django.core.urlresolvers import reverse
from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    # On 403s, add a link to the API documentation.
    if response is not None:
        if response.status_code == 403:
            api_url = context['request'].build_absolute_uri(reverse('api'))
            response.data['detail'] += u' See %s for details.' % api_url

    return response
