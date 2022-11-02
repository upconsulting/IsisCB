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
        'tenants': [rule.tenant for rule in rules if rule.allowed_action == TenantRule.UPDATE],
        'all':Tenant.objects.all()
    }
    return render(request, 'curation/tenants_list.html', context=context)
