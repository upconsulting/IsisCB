from django.shortcuts import render
from django.contrib.admin.views.decorators import user_passes_test


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def import_json(request):
    
    context = {
        'curation_section': 'import',
    }

    template = 'jsonimport/import_json.html'
    return render(request, template, context)

