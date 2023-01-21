from django.shortcuts import render, get_object_or_404
from isisdata.models import *
import isisdata.views as isisdata_views

# Create your views here.

def home(request, tenant_id):
    context = {
        'active': 'home',
        'tenant_id': tenant_id,
    }
    tenant = Tenant.objects.filter(identifier=tenant_id).first()
    
    if tenant and tenant.use_home_page_template:
        # this is super ugly but works for our special case right now
        # TODO: extract common code and make configurable
        return isisdata_views.home(request, tenant.home_page_template)
    return render(request, 'tenants/home.html', context=context)
