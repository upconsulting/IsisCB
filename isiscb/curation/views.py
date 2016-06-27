from django.template import RequestContext, loader
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse #, HttpResponseForbidden, Http404, HttpResponseRedirect, JsonResponse


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
    return HttpResponse('')


@staff_member_required
def authority(request, authority_id=None):
    return HttpResponse('')


@staff_member_required
def dataset(request, dataset_id=None):
    return HttpResponse('')


@staff_member_required
def users(request, user_id=None):
    return HttpResponse('')
