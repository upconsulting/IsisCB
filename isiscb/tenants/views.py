from django.shortcuts import render

# Create your views here.

def home(request, tenantid):
    print("here")

    context = {
        'active': 'home',
        'tenant_id': tenantid,
    }
    return render(request, 'tenants/home.html', context=context)
