from isisdata.models import Tenant, TenantRule
from django.shortcuts import get_object_or_404

def add_tenants(request):
    if request.user:
        for role in request.user.isiscb_roles.all():
            if role.tenant_rules:
                # there should only be one
                if role.tenant_rules[0].tenant:
                    return {'tenant_id': role.tenant_rules[0].tenant.id , 'tenant': role.tenant_rules[0].tenant}
    return {}
