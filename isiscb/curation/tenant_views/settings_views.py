from isisdata.models import *
from curation.forms import TenantSettingsForm
from django.shortcuts import get_object_or_404, render, redirect

from django.contrib.admin.views.decorators import user_passes_test

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def list_tenants(request):

    roles = request.user.isiscbrole_set.filter(accessrule__tenantrule__tenant__isnull=False)
    tenant_rules = set()
    for rules in [role.tenant_rules.all() for role in roles]:
        tenant_rules.update(rules)
    context = {
        'tenants': [(rule.tenant, rule.allowed_action) for rule in tenant_rules if rule.allowed_action in [TenantRule.UPDATE, TenantRule.VIEW]],
        'all':Tenant.objects.all()
    }
    return render(request, 'curation/tenants_list.html', context=context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def tenant_settings(request, tenant_pk):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    context = {
        'tenant': tenant
    }

    form = TenantSettingsForm(request.POST or None, instance=tenant.settings)
    if request.method == 'POST':
        if form.is_valid():
            # if it's the first time, set the settings object
            if not tenant.settings:
                tenant.settings = form.save()
                tenant.save()
            else:
                form.save()

    context.update({
        'form': form
    })
    return render(request, 'curation/tenant_settings.html', context=context)
