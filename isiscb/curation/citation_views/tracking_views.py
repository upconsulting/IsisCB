from __future__ import unicode_literals
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
    citation = get_object_or_404(Citation, pk=citation_id)

    if request.method == 'POST':
        tracking.delete()
        citation.save()

    result = {
        'action': 'delete',
        'result': 'success',
        'state': citation.tracking_state
    }
    return JsonResponse(result)

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def proof_and_set_active(request, citation_id):
    citation = get_object_or_404(Citation, pk=citation_id)

    search_key = ''
    current_index = ''
    if request.method == 'POST':
        search_key = request.POST.get('search', request.POST.get('search'))
        current_index = request.POST.get('current', request.POST.get('current'))

        def create_track_record(track_type):
            if not citation.tracking_records.filter(type_controlled=track_type):
                tracking = Tracking()
                tracking.type_controlled = track_type
                tracking.modified_by = request.user
                date = datetime.datetime.now()
                tracking.tracking_info = date.strftime("%Y/%m/%d") + " {} {}".format(request.user.first_name, request.user.last_name)
                tracking.citation = citation
                tracking.save()
                citation.save()

        create_track_record(Tracking.FULLY_ENTERED)
        create_track_record(Tracking.PROOFED)

        citation.record_status_value = CuratedMixin.ACTIVE
        citation.save()

    target = reverse('curation:curate_citation', args=(citation_id,))
    if search_key and current_index:
        target += '&search=%s&current=%s' % (search_key, current_index)

    return HttpResponseRedirect(target)
