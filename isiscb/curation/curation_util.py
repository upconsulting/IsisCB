from isisdata.models import *
import itertools
import logging

logger = logging.getLogger(__name__)

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

def get_tenant_access(user, tenant):
    if not user.is_authenticated:
        return None
    
    # superusers can do anything
    if user.is_superuser:
        return TenantRule.UPDATE
    
    tenant_roles = user.isiscb_roles.filter(Q(accessrule__tenantrule__tenant__isnull=False))
    if tenant_roles:
        if TenantRule.UPDATE in [trule.allowed_action for trole in tenant_roles for trule in trole.tenant_rules]:
            return TenantRule.UPDATE
        else:
            return TenantRule.VIEW

    return None

def get_classification_systems(user):
    tenant_query = Q(owning_tenant=get_tenant(user)) | Q(owning_tenant__isnull=True)
    return ClassificationSystem.objects.filter(tenant_query)

def get_default_classification_system(classification_systems):
    return next((sys for sys in classification_systems if sys.is_default), None)

        