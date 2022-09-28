from django.shortcuts import render

# Create your views here.

def home(request, tenant_id):
    context = {
        'active': 'home',
        'tenant_id': tenant_id,
    }
    return render(request, 'tenants/home.html', context=context)
