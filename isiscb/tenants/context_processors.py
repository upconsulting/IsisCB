from isisdata.models import Tenant

def add_tenants(request):
    return {'tenant_id':  request.GET.get('tenant', '')}
