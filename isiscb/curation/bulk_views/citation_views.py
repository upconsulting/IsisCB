from django.contrib.admin.views.decorators import staff_member_required, user_passes_test
from django.http import HttpResponseRedirect, JsonResponse

from django.shortcuts import get_object_or_404, render, redirect
from django.core.urlresolvers import reverse

from django.utils.http import urlencode

from isisdata.models import *
from isisdata import tasks as data_tasks

from curation.forms import *

import curation.rules as rules

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def bulk_create_ccr(request):

    if request.method == 'POST':
        cctype = request.POST.get('CCRType', None)
        ccr_subject_id = request.POST.get('ccrSubject', None)
        ccr_pasted_subject_id = request.POST.get('pastedCitationId', None)

        if not ccr_subject_id and not ccr_pasted_subject_id:
            return JsonResponse({"msg": "No citation id provided"}, status=403)

        # pasted id gets precedence over dropdown
        if ccr_pasted_subject_id:
            ccr_subject = get_object_or_404(Citation, pk=ccr_pasted_subject_id)
        else:
            ccr_subject = get_object_or_404(Citation, pk=ccr_subject_id)
        citation_ids  = request.POST.getlist('citationId', None)

        if not rules.can_edit_record(request.user, ccr_subject):
            return JsonResponse({"msg": "User does is not allowed to change subject citation."}, status=403)

        failed = []
        success = []
        now = datetime.datetime.now().strftime('%Y-%m-%d at %I:%M%p')
        for citation_id in citation_ids:
            ccr_object = get_object_or_404(Citation, pk=citation_id)
            if not rules.can_edit_record(request.user, ccr_object):
                failed.append(citation_id)
                continue

            ccrelation = CCRelation()
            if cctype is not CCRelation.REVIEW_OF:
                ccrelation.object = ccr_object
                ccrelation.subject = ccr_subject
            else:
                ccrelation.object = ccr_subject
                ccrelation.subject = ccr_object

            ccrelation.type_controlled = cctype
            if ccr_object.part_details:
                ccrelation.data_display_order = ccr_object.part_details.page_begin
            ccrelation.record_history = "This record has been created as part of a bulk CCRelation creation on " + now + "."
            ccrelation.save()

            success.append(citation_id)

    return JsonResponse({'success': success, 'failed': failed})
