from django.http import HttpResponse, HttpResponseForbidden, Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect

from isisdata.models import *

import datetime
from django.utils import timezone

from itertools import chain

def recent_records(request):
    """
    The landing view, at /.
    """

    interval = request.GET.get('interval', 'month')
    days = 31
    if interval == 'week':
        days = 7

    recent_records =[]

    # ISISCB-1045: remove limit of recent records
    nr_of_records = 20
    start_index = 0
    end_index = nr_of_records

    citations_done = False
    authorities_done = False
    # unfortunately, citatations freshly created are public=False so we can't filter on that field when retrieving
    # creation events, we have to test that after we got the real object form the history object
    recent_citations = Citation.history.filter(history_type="+").order_by('-history_date')[start_index:end_index] if not citations_done else []
    recent_authorities = Authority.history.filter(history_type="+").order_by('-history_date')[start_index:end_index] if not authorities_done else []
    while not ((citations_done or not recent_citations) and (authorities_done or recent_authorities)):
        lastMonth = timezone.now() - datetime.timedelta(days=days)

        for record in sorted(chain(recent_citations, recent_authorities), key=lambda rec: rec.history_date, reverse=True):
            record = Citation.objects.get(pk=record.id) if type(record) is HistoricalCitation else Authority.objects.get(pk=record.id)
            if record.public:
                if record.created_on > lastMonth:
                    recent_records.append(record)
                else:
                    if type(record) is HistoricalCitation:
                        citations_done = True
                    else:
                        authorities_done = True

        start_index = end_index + 1
        end_index = end_index + 10
        recent_citations = Citation.history.filter(history_type="+").order_by('-history_date')[start_index:end_index] if not citations_done else []
        recent_authorities = Authority.history.filter(history_type="+").order_by('-history_date')[start_index:end_index] if not authorities_done else []

    context = {
        'active': 'home',
        'records_recent': recent_records,
        # not very pretty but good enough for now
        'interval': interval,
    }
    return render(request, 'isisdata/recent_records.html', context=context)
