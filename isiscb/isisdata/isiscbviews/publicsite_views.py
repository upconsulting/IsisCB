from django.http import HttpResponse, HttpResponseForbidden, Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect

from isisdata.models import *

import datetime
from django.utils import timezone

from itertools import chain

def last_month_records(request):
    """
    The landing view, at /.
    """

    interval = request.GET.get('interval', 'month')
    days = 31
    if interval == 'week':
        days = 7

    recent_records =[]

    nr_of_records = 20
    start_index = 0
    end_index = nr_of_records

    done = False
    # unfortunately, citatations freshly created are public=False so we can't filter on that field when retrieving
    # creation events, we have to test that after we got the real object form the history object
    while len(recent_records) < nr_of_records and not done:
        recent_citations = Citation.history.filter(history_type="+").order_by('-history_date')[start_index:end_index]
        recent_authorities = Authority.history.filter(history_type="+").order_by('-history_date')[start_index:end_index]

        lastMonth = timezone.now() - datetime.timedelta(days=days)
        print lastMonth

        for record in sorted(chain(recent_citations, recent_authorities), key=lambda rec: rec.history_date, reverse=True):
            record = Citation.objects.get(pk=record.id) if type(record) is HistoricalCitation else Authority.objects.get(pk=record.id)
            if record.public:
                print record.created_on
                if record.created_on > lastMonth:
                    recent_records.append(record)
                else:
                    done = True
                    break

        start_index = end_index + 1
        end_index = end_index + 10

    context = {
        'active': 'home',
        'records_recent': recent_records[:nr_of_records],
        # not very pretty but good enough for now
        'interval': interval,
    }
    return render(request, 'isisdata/recent_records.html', context=context)
