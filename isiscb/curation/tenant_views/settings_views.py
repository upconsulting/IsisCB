from isisdata.models import *

from django.contrib.admin.views.decorators import user_passes_test

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def list_tenants(request):
    pass
