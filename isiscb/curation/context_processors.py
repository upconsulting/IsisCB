from isisdata.models import Tenant, TenantRule
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import AnonymousUser

def add_tenants(request):
    if request.user and not request.user.is_anonymous:
        for role in request.user.isiscb_roles.all():
            if role.tenant_rules:
                # there should only be one
                if role.tenant_rules[0].tenant:
                    return {'tenant_id': role.tenant_rules[0].tenant.id , 'tenant': role.tenant_rules[0].tenant}
    return {}
