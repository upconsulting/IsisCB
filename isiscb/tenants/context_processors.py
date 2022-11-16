from isisdata.models import Tenant
from django.shortcuts import get_object_or_404

def add_tenants(request):
    if 'tenant_id' in request.resolver_match.kwargs:
        tenant_id = request.resolver_match.kwargs['tenant_id']
        return {'tenant_id': tenant_id , 'tenant': get_object_or_404(Tenant, identifier=tenant_id) if tenant_id else None}
    return {}
