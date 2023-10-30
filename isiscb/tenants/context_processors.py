from isisdata.models import Tenant
from django.shortcuts import get_object_or_404

def add_tenants(request):
    context = {}
    if 'tenant_id' in request.resolver_match.kwargs:
        tenant_id = request.resolver_match.kwargs['tenant_id']
        context.update({
            'tenant_id': tenant_id , 
            'tenant': get_object_or_404(Tenant, identifier=tenant_id) if tenant_id else None
        }) 
    context.update({
        'include_all_tenants': request.include_all_tenants
    })

    return context
