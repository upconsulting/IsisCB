from isisdata.models import *
from curation.forms import TenantSettingsForm, TenantPageBlockForm, TenantPageBlockColumnForm
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
        'tenant': tenant,
        'selected': 'general'
    }
    return render(request, 'curation/tenants/tenant.html', context=context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def tenant_home_page(request, tenant_pk):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    context = {
        'tenant': tenant,
        'selected': 'home_page'
    }
    return render(request, 'curation/tenants/tenant_home_page.html', context=context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def tenant_add_page_block(request, tenant_pk, block_type=None):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    context = {
        'tenant': tenant,
        'block_type': block_type if block_type else 'main'
    }

    type_map = {
        'home': TenantPageBlock.HOME_MAIN,
        'main': TenantPageBlock.HOME_OTHER,
        'about': TenantPageBlock.ABOUT
    }
    block_type = type_map[block_type] if block_type else type_map['main']
    
    if request.method == 'POST':
        form = TenantPageBlockForm(request.POST)

        if form.is_valid():
            block = TenantPageBlock()
            block.block_index = form.cleaned_data['block_index']
            block.nr_of_columns = form.cleaned_data['nr_of_columns']
            block.title = form.cleaned_data['title']
            block.tenant_settings = tenant.settings
            block.block_type = block_type
            block.save()
            return redirect(reverse('curation:tenant_home_page', kwargs={'tenant_pk':tenant_pk}))
    else:
        context.update({
            'form': TenantPageBlockForm(),
        })
    return render(request, 'curation/tenants/add_page_block.html', context=context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def tenant_edit_page_block(request, tenant_pk, block_id):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    block = get_object_or_404(TenantPageBlock, pk=block_id)

    type_map = {
        TenantPageBlock.HOME_MAIN: 'home',
        TenantPageBlock.HOME_OTHER: 'main',
        TenantPageBlock.ABOUT: 'about'
    }
    context = {
        'tenant': tenant,
        'block_id': block_id,
        'block_type': type_map.get(block.block_type, 'home')
    }

    if request.method == 'POST':
        form = TenantPageBlockForm(request.POST)
        if form.is_valid():
            block.block_index = form.cleaned_data['block_index']
            block.nr_of_columns = form.cleaned_data['nr_of_columns']
            block.title = form.cleaned_data['title']
            block.save()
            return redirect(reverse('curation:tenant_home_page', kwargs={'tenant_pk':tenant_pk}))
    else:
        context.update({
            'form': TenantPageBlockForm(initial={
                'block_index': block.block_index,
                'nr_of_columns': block.nr_of_columns,
                'title': block.title
            }),
        })
    return render(request, 'curation/tenants/add_page_block.html', context=context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def tenant_add_column_content(request, tenant_pk, page_block_id):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    page_block = get_object_or_404(TenantPageBlock, pk=page_block_id)
    context = {
        'tenant': tenant,
        'page_block': page_block,
        'form': TenantPageBlockColumnForm()
    }

    if request.method == 'POST':
        form = TenantPageBlockColumnForm(request.POST)
        if form.is_valid():
            column = TenantPageBlockColumn()
            column.column_index = form.cleaned_data['column_index']
            column.content = form.cleaned_data['content']
            column.page_block = page_block
            column.save()

            return redirect(reverse('curation:tenant_home_page', kwargs={'tenant_pk':tenant_pk}))

    return render(request, 'curation/tenants/add_column_content.html', context=context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def tenant_delete_column_content(request, tenant_pk, page_block_id, content_id):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    page_block = get_object_or_404(TenantPageBlock, pk=page_block_id)
    content = get_object_or_404(TenantPageBlockColumn, pk=content_id)

    if request.method == 'POST':
        content.delete()

    return redirect(reverse('curation:tenant_home_page', kwargs={'tenant_pk':tenant_pk}))

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def tenant_edit_column_content(request, tenant_pk, page_block_id, content_id):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    page_block = get_object_or_404(TenantPageBlock, pk=page_block_id)
    content = get_object_or_404(TenantPageBlockColumn, pk=content_id)

    context = {
        'tenant': tenant,
        'page_block': page_block,
        'content_id': content_id,
        'form': TenantPageBlockColumnForm(initial={
            'column_index': content.column_index,
            'content': content.content,

        })
    }

    if request.method == 'POST':
        form = TenantPageBlockColumnForm(request.POST)
        if form.is_valid():
            content.column_index = form.cleaned_data['column_index']
            content.content = form.cleaned_data['content']
            content.page_block = page_block
            content.save()

            return redirect(reverse('curation:tenant_home_page', kwargs={'tenant_pk':tenant_pk})) 

    return render(request, 'curation/tenants/add_column_content.html', context=context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def tenant_delete_page_block(request, tenant_pk, page_block_id):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    page_block = get_object_or_404(TenantPageBlock, pk=page_block_id)

    if request.method == 'POST':
        page_block.delete()

    return redirect(reverse('curation:tenant_home_page', kwargs={'tenant_pk':tenant_pk}))

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def tenant_about_page(request, tenant_pk):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    context = {
        'tenant': tenant,
        'selected': 'about'
    }
    return render(request, 'curation/tenants/about.html', context=context)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def tenant_settings(request, tenant_pk):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    context = {
        'tenant': tenant
    }

    form = TenantSettingsForm(request.POST or None, request.FILES or None, instance=tenant.settings)
    if request.method == 'POST':
        if form.is_valid():
            # if it's the first time, set the settings object
            tenant.title = form.cleaned_data['title']
            tenant.logo = form.cleaned_data['logo']
            tenant.contact_email = form.cleaned_data['contact_email']
            if not tenant.settings:
                tenant.settings = form.save()
            else:
                form.save()
            tenant.save()
            return redirect(reverse('curation:tenant', kwargs={'tenant_pk':tenant_pk}))

    context.update({
        'form': form
    })
    return render(request, 'curation/tenants/tenant_settings.html', context=context)

