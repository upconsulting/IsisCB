from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from rest_framework.reverse import reverse
from isisdata.models import SearchQuery, Tenant
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import logging
logger = logging.getLogger(__name__)

@login_required
def searches_saved(request):
    """
    Provides saved searches for a logged-in user.
    """

    searchqueries = request.user.searches.filter(saved=True).order_by('-created_on')
    
    paginator = Paginator(searchqueries, 10)

    page = request.GET.get('page')
    try:
        searchqueries = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        searchqueries = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        searchqueries = paginator.page(paginator.num_pages)

    context = {
        'searchqueries': searchqueries,
        'tenants': Tenant.objects.all()
    }
    return render(request, 'isisdata/search_saved.html', context)

@login_required
@require_http_methods(["POST"])
def save_search(request, pk):
    instance = SearchQuery.objects.get(pk=pk)
    instance.saved = True
    instance.save()
    return redirect('search_saved')

@login_required
@require_http_methods(["POST"])
def remove_saved_search(request, pk):
    instance = SearchQuery.objects.get(pk=pk)
    instance.saved = False
    instance.save()
    return redirect('search_saved')

@login_required
def search_history(request):
    """
    Provides the search history for a logged-in user.
    """

    # If the user is Anonymous, redirect them to the login view.
    if type(request.user._wrapped) is not User:
        return HttpResponseRedirect(reverse('login'))

    searchqueries = request.user.searches.order_by('-created_on')

    paginator = Paginator(searchqueries, 10)

    page = request.GET.get('page')
    try:
        searchqueries = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        searchqueries = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        searchqueries = paginator.page(paginator.num_pages)

    context = {
        'searchqueries': searchqueries,
        'tenants': Tenant.objects.all()
    }
    return render(request, 'isisdata/search_history.html', context)