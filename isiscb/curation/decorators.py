
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied

import curation.curation_util as c_util
from isisdata.models import *

def is_tenant_admin(view_func):
    """
    Decorator for views that checks if the user has admin priviledges to the
    given tenant.
    """

    def decorator(request, **kwargs):
        if 'tenant_pk' not in kwargs:
            raise PermissionDenied
        tenant = get_object_or_404(Tenant, pk=kwargs['tenant_pk'])
        access = c_util.get_tenant_access(request.user, tenant)
        if access == TenantRule.UPDATE:
            return view_func(request, **kwargs)
        print("Permission denied to", tenant)
        raise PermissionDenied
    return decorator
