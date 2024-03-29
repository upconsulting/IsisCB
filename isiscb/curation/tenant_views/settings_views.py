from isisdata.models import *
from curation.forms import TenantSettingsForm, TenantPageBlockForm, TenantPageBlockColumnForm, TenantImageUploadForm
from django.shortcuts import get_object_or_404, render, redirect, reverse, resolve_url
from urllib.parse import urlparse

from django.contrib.admin.views.decorators import user_passes_test
from curation.decorators import is_tenant_admin
import curation.curation_util as c_util

# the following map is used to determine which view should be redirected to
# after a block or column content has been added or edited.
redirect_map = {
    TenantPageBlock.HOME_MAIN: 'curation:tenant_home_page',
    TenantPageBlock.HOME_OTHER: 'curation:tenant_home_page',
    TenantPageBlock.ABOUT: 'curation:tenant_about'
}

# the following map is used to determine where to redirect to after an image
# has been added/edited
image_redirect_map = {
    TenantImage.ABOUT: 'curation:tenant_about',
    TenantImage.AUTHORITY_DEFAULT_IMAGE_AUTHOR: 'curation:tenant_content_page',
}

@is_tenant_admin
def list_tenants(request):

    roles = request.user.isiscb_roles.filter(accessrule__tenantrule__tenant__isnull=False)
    tenant_rules = set()
    for rules in [role.tenant_rules.all() for role in roles]:
        tenant_rules.update(rules)
    context = {
        'tenants': [(rule.tenant, rule.allowed_action) for rule in tenant_rules if rule.allowed_action in [TenantRule.UPDATE, TenantRule.VIEW]],
        'all':Tenant.objects.all()
    }
    return render(request, 'curation/tenants/tenants_list.html', context=context)

@is_tenant_admin
def tenant(request, tenant_pk):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    context = {
        'tenant': tenant,
        'selected': 'general'
    }
    return render(request, 'curation/tenants/tenant.html', context=context)

@is_tenant_admin
def tenant_home_page(request, tenant_pk):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    context = {
        'tenant': tenant,
        'selected': 'home_page'
    }
    return render(request, 'curation/tenants/tenant_home_page.html', context=context)

@is_tenant_admin
def tenant_add_page_block(request, tenant_pk, block_type=None):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    context = {
        'tenant': tenant,
        'block_type': block_type if block_type else 'main'
    }

    type_template_map = {
        'home': 'curation:tenant_home_page',
        'main': 'curation:tenant_home_page',
        'about': 'curation:tenant_about'
    }
    template = type_template_map[block_type] if block_type else type_template_map['main']
    
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
            return redirect(reverse(template, kwargs={'tenant_pk':tenant_pk}))
    else:
        context.update({
            'form': TenantPageBlockForm(),
        })
    return render(request, 'curation/tenants/add_page_block.html', context=context)

@is_tenant_admin
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

    redirect_view = redirect_map.get(block.block_type, 'curation:tenant_home_page')

    if request.method == 'POST':
        form = TenantPageBlockForm(request.POST)
        if form.is_valid():
            block.block_index = form.cleaned_data['block_index']
            block.nr_of_columns = form.cleaned_data['nr_of_columns']
            block.title = form.cleaned_data['title']
            block.save()
            return redirect(reverse(redirect_view, kwargs={'tenant_pk':tenant_pk}))
    else:
        context.update({
            'form': TenantPageBlockForm(initial={
                'block_index': block.block_index,
                'nr_of_columns': block.nr_of_columns,
                'title': block.title
            }),
        })
    return render(request, 'curation/tenants/add_page_block.html', context=context)

@is_tenant_admin
def tenant_delete_page_block(request, tenant_pk, page_block_id):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    page_block = get_object_or_404(TenantPageBlock, pk=page_block_id)

    redirect_view = redirect_map.get(page_block.block_type, 'curation:tenant_home_page')

    if request.method == 'POST':
        page_block.delete()

    return redirect(reverse(redirect_view, kwargs={'tenant_pk':tenant_pk}))


@is_tenant_admin
def tenant_add_column_content(request, tenant_pk, page_block_id):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    page_block = get_object_or_404(TenantPageBlock, pk=page_block_id)
    context = {
        'tenant': tenant,
        'page_block': page_block,
        'form': TenantPageBlockColumnForm()
    }

    redirect_view = redirect_map.get(page_block.block_type, 'curation:tenant_home_page')


    if request.method == 'POST':
        form = TenantPageBlockColumnForm(request.POST)
        if form.is_valid():
            column = TenantPageBlockColumn()
            column.column_index = form.cleaned_data['column_index']
            column.content = form.cleaned_data['content']
            column.page_block = page_block
            column.save()

            return redirect(reverse(redirect_view, kwargs={'tenant_pk':tenant_pk}))

    return render(request, 'curation/tenants/add_column_content.html', context=context)

@is_tenant_admin
def tenant_delete_column_content(request, tenant_pk, page_block_id, content_id):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    page_block = get_object_or_404(TenantPageBlock, pk=page_block_id)
    content = get_object_or_404(TenantPageBlockColumn, pk=content_id)

    if request.method == 'POST':
        content.delete()

    redirect_view = redirect_map.get(page_block.block_type, 'curation:tenant_home_page')
    return redirect(reverse(redirect_view, kwargs={'tenant_pk':tenant_pk}))

@is_tenant_admin
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

            return redirect(reverse(redirect_map[page_block.block_type], kwargs={'tenant_pk':tenant_pk})) 

    return render(request, 'curation/tenants/add_column_content.html', context=context)

@is_tenant_admin
def tenant_about_page(request, tenant_pk):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    context = {
        'tenant': tenant,
        'selected': 'about',
        'images': tenant.settings.about_images if tenant.settings else None
    }
    return render(request, 'curation/tenants/about.html', context=context)

@is_tenant_admin
def tenant_delete_image(request, tenant_pk, image_id):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    context = {
        'tenant': tenant,
        'selected': 'about'
    }

    redirect_to = 'curation:about'
    if request.method == "POST":
        image =get_object_or_404(TenantImage, pk=image_id)
        redirect_to = image_redirect_map[image.image_type]
        image.delete()

    return redirect(reverse(redirect_to, kwargs={'tenant_pk':tenant_pk}))

@is_tenant_admin
def tenant_edit_image(request, tenant_pk, image_id):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    image = get_object_or_404(TenantImage, pk=image_id)
    context = {
        'tenant': tenant,
        'selected': 'about',
        'image': image
    }

    if request.method == 'GET':
        form = TenantImageUploadForm({
            'title': image.title, 
            'image_index': image.image_index,
            'image_type': image.image_type,
            })
        context.update({
            'form': form,
            'image_type': 'about' if image.image_type == TenantImage.ABOUT else 'authority_default'
        })
        return render(request, 'curation/tenants/tenant_edit_image.html', context=context)

    return redirect(reverse(image_redirect_map[image.image_type] if image.image_type in image_redirect_map else 'curation:tenant_about', kwargs={'tenant_pk':tenant_pk}))
    



@is_tenant_admin
def tenant_add_save_image(request, tenant_pk, image_id=None, image_type=None):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)

    page_map = {
        'about': 'about',
        'authority_default': 'content'
    }
    context = {
        'tenant': tenant,
        'image_type': image_type,
        'selected': page_map[image_type] if image_type else 'about'
    }

    if image_id:
        request.FILES['image'] = get_object_or_404(TenantImage, pk=image_id).image
    form = TenantImageUploadForm(request.POST or None, request.FILES or None)

    if request.method == 'POST':
        if form.is_valid():
            if not image_id:
                image = TenantImage()
                image.tenant_settings = tenant.settings
                image.image = form.cleaned_data['image']

                if image_type == 'about':
                    image.image_type = TenantImage.ABOUT
                else:
                    image.image_type = request.GET.get('default_type', TenantImage.AUTHORITY_DEFAULT_IMAGE_AUTHOR)
            else:
                image = get_object_or_404(TenantImage, pk=image_id)
            image.title = form.cleaned_data['title']
            image.image_index = form.cleaned_data['image_index']
            image.link = form.cleaned_data['link']
            image.save()
            
            return redirect(reverse(image_redirect_map[image.image_type] if image.image_type in image_redirect_map else 'curation:tenant_about', kwargs={'tenant_pk':tenant_pk}))
    else:
        context.update({
            'form': form,
            'image_choices': [
                (TenantImage.AUTHORITY_DEFAULT_IMAGE_AUTHOR, "Default image for author"), 
                (TenantImage.AUTHORITY_DEFAULT_IMAGE_PERSON, "Default image for person"),
                (TenantImage.AUTHORITY_DEFAULT_IMAGE_CLASS_TERM, "Default image for category division"),
                (TenantImage.AUTHORITY_DEFAULT_IMAGE_CONCEPT, "Default image for concept"),
                (TenantImage.AUTHORITY_DEFAULT_IMAGE_GEO_TERM, "Default image for geographic term"),
                (TenantImage.AUTHORITY_DEFAULT_IMAGE_INSTITUTION, "Default image for institution"),
                (TenantImage.AUTHORITY_DEFAULT_IMAGE_PUBLISHER, "Default image for publisher"),
                (TenantImage.AUTHORITY_DEFAULT_IMAGE_TIMEPERIOD, "Default image for time period"),
            ]
        })
    
    return render(request, 'curation/tenants/tenant_edit_image.html', context=context)

@is_tenant_admin
def tenant_content_page(request, tenant_pk):
    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    context = {
        'tenant': tenant,
        'selected': 'content',
    }
    return render(request, 'curation/tenants/tenant_content_page.html', context=context)

@is_tenant_admin
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
            tenant.blog_url = form.cleaned_data['blog_url']
            tenant.status = form.cleaned_data['status']
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

