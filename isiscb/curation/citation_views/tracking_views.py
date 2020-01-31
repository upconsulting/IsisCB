from django.contrib.admin.views.decorators import staff_member_required, user_passes_test
from django.http import HttpResponseRedirect, JsonResponse

from django.shortcuts import get_object_or_404, render, redirect
from django.core.urlresolvers import reverse

from django.utils.http import urlencode

from isisdata.models import *
from curation.tracking import TrackingWorkflow

from curation.contrib.views import check_rules
from curation import tasks as curation_tasks
import curation.view_helpers as view_helpers

from rules.contrib.views import objectgetter

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def delete_tracking_for_citation(request, citation_id, tracking_id):
    tracking = get_object_or_404(Tracking, pk=tracking_id)

    if request.method == 'POST':
        tracking.delete()

    result = {
        'action': 'delete',
        'result': 'success'
    }
    return JsonResponse(result)
