from isisdata.models import *
import itertools

def get_tenants(user):
    if user.is_superuser:
        return Tenant.objects.all()

    tenant_roles = user.isiscb_roles.filter(Q(accessrule__tenantrule__tenant__isnull=False))
    tenants_rules = [t.tenant_rules for t in tenant_roles]
    tenants = [t.tenant.id for t in itertools.chain.from_iterable(tenants_rules)]
    return Tenant.objects.filter(id__in=tenants)

def get_tenant(user):
    """ A user should have access to only one tenant."""
    tenant_roles = filter(lambda role : role.tenant_rules and role.tenant_rules[0].tenant, user.isiscb_roles.all())
    if tenant_roles:
        tenant_role = next(tenant_roles, None)
    if tenant_role:
        return tenant_role.tenant_rules[0].tenant
    return None
