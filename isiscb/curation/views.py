from django.template import RequestContext, loader
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse #, HttpResponseForbidden, Http404, HttpResponseRedirect, JsonResponse

from isisdata.models import *
from curation.filters import *

import iso8601



@staff_member_required
def dashboard(request):
    """
    """
    template = loader.get_template('curation/dashboard.html')
    context = RequestContext(request, {
    })
    return HttpResponse(template.render(context))


@staff_member_required
def citation(request, citation_id=None):
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
    })
    if citation_id:
        pass
    else:
        template = loader.get_template('curation/citation_list_view.html')
        filtered_objects = CitationFilter(request.GET, queryset=Citation.objects.all())
        
        context.update({
            'objects': filtered_objects,
            'filters_active': len([v for k, v in request.GET.iteritems()
                                   if len(v) > 0 and k != 'page']) > 0,
        })
        return HttpResponse(template.render(context))


@staff_member_required
def authority(request, authority_id=None):
    context = RequestContext(request, {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
    })
    if authority_id:
        pass
    else:
        template = loader.get_template('curation/list_view.html')
        filtered_objects = AuthorityFilter(request.GET, queryset=Authority.objects.all())
        context.update({
            'objects': filtered_objects,
            'filters_active': len([v for k, v in request.GET.iteritems()
                                   if len(v) > 0 and k != 'page']) > 0,
        })
        return HttpResponse(template.render(context))


@staff_member_required
def dataset(request, dataset_id=None):
    return HttpResponse('')


@staff_member_required
def users(request, user_id=None):
    return HttpResponse('')
