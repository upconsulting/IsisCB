from isisdata.models import *
from curation.forms import TenantSettingsForm, TenantPageBlockForm
from django.shortcuts import get_object_or_404, render, redirect, reverse

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
    return render(request, 'curation/tenants/tenants_list.html', context=context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def tenant(request, tenant_pk):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    context = {
        'tenant': tenant
    }
    return render(request, 'curation/tenants/tenant.html', context=context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def tenant_add_page_block(request, tenant_pk):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    context = {
        'tenant': tenant
    }
    if request.method == 'POST':
        form = TenantPageBlockForm(request.POST)
        if form.is_valid():
            block = TenantPageBlock()
            block.block_index = form.cleaned_data['block_index']
            block.nr_of_columns = form.cleaned_data['nr_of_columns']
            block.tenant_settings = tenant.settings
            block.save()
            return redirect(reverse('curation:tenant', kwargs={'tenant_pk':tenant_pk}))
    else:
        context.update({
            'form': TenantPageBlockForm()
        })
    return render(request, 'curation/tenants/add_page_block.html', context=context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def tenant_delete_page_block(request, tenant_pk, page_block_id):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    page_block = get_object_or_404(TenantPageBlock, pk=page_block_id)

    if request.method == 'POST':
        page_block.delete()

    return redirect(reverse('curation:tenant', kwargs={'tenant_pk':tenant_pk}))


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
                tenant.title = form.cleaned_data['title']
                tenant.settings = form.save()
                tenant.save()
            else:
                tenant.title = form.cleaned_data['title']
                form.save()
                tenant.save()

    context.update({
        'form': form
    })
    return render(request, 'curation/tenants/tenant_settings.html', context=context)
