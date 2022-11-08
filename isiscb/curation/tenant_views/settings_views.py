from isisdata.models import *
from django.shortcuts import get_object_or_404, render, redirect

from django.contrib.admin.views.decorators import user_passes_test

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def list_tenants(request):

    roles = request.user.isiscbrole_set.filter(accessrule__tenantrule__tenant__isnull=False)
    tenant_rules = []
    for rules in [role.tenant_rules.all() for role in roles]:
        tenant_rules.append(rules)
    context = {
        'tenants': [(rule.tenant, rule.allowed_action) for rule in rules if rule.allowed_action in [TenantRule.UPDATE, TenantRule.VIEW]],
        'all':Tenant.objects.all()
    }
    return render(request, 'curation/tenants_list.html', context=context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def tenant_settings(request, tenant_id):
    tenant = get_object_or_404(Tenant, pk=tenant_id)
    context = {
        'tenant': tenant,
    }
    return render(request, 'curation/tenant_settings.html', context=context)
