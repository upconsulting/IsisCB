from __future__ import unicode_literals
from django.http import HttpResponse, HttpResponseForbidden, Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect

from isisdata.models import *

import datetime
from django.utils import timezone

from itertools import chain


NR_OF_RECENT_RECORDS = 20

def recent_records(request):
    """
    The landing view, at /.
    """

    interval = request.GET.get('interval', 'month')
    days = 31
    if interval == 'week':
        days = 7

    recent_records, last_processed = _get_recent_records_range(0, NR_OF_RECENT_RECORDS, days)

    context = {
        'active': 'home',
        'records_recent': recent_records,
        # not very pretty but good enough for now
        'interval': interval,
        'last_processed': last_processed
    }
    return render(request, 'isisdata/recent_records.html', context=context)

# ISISCB-1045: lazy load reords
def recent_records_range(request):
    interval = request.GET.get('interval', 'month')
    days = 31
    if interval == 'week':
        days = 7

    last_processed = int(request.GET.get('last_processed', -1)) + 1

    recent_records, last_processed = _get_recent_records_range(last_processed, last_processed+NR_OF_RECENT_RECORDS, days)

    context = {
        'active': 'home',
        'records_recent': recent_records,
        # not very pretty but good enough for now
        'interval': interval,
        'last_processed': last_processed
    }

    return render(request, 'isisdata/fragment_recent_records.html', context=context)

def _get_recent_records_range(start_index, end_index, days):
    citations_done = False
    authorities_done = False
    # unfortunately, citatations freshly created are public=False so we can't filter on that field when retrieving
    # creation events, we have to test that after we got the real object form the history object
    recent_citations = Citation.history.filter(history_type="+").order_by('-history_date')[start_index:end_index] if not citations_done else []
    recent_authorities = Authority.history.filter(history_type="+").order_by('-history_date')[start_index:end_index] if not authorities_done else []
    lastMonth = timezone.now() - datetime.timedelta(days=days)

    last_processed = start_index
    def is_done():
        return ((citations_done or not recent_citations) and (authorities_done or not recent_authorities))

    recent_records = []
    while not is_done():
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
            if len(recent_records) == NR_OF_RECENT_RECORDS:
                citations_done = True
                authorities_done = True

        start_index = end_index + 1
        last_processed = end_index
        end_index = end_index + 10
        if is_done():
            break

        recent_citations = Citation.history.filter(history_type="+").order_by('-history_date')[start_index:end_index] if not citations_done else []
        recent_authorities = Authority.history.filter(history_type="+").order_by('-history_date')[start_index:end_index] if not authorities_done else []

    return recent_records, last_processed
