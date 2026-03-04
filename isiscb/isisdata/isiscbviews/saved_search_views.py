from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, JsonResponse
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
    return JsonResponse({'search_id': pk, 'status': 'success'})

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

@login_required
@require_http_methods(["POST"])
def clear_history(request):
    """
    Deletes all the search queries that have not been saved for a logged-in user.
    """

    # If the user is Anonymous, redirect them to the login view.
    if type(request.user._wrapped) is not User:
        return HttpResponseRedirect(reverse('login'))

    request.user.searches.filter(saved=False).delete()

    return redirect('search_history')

@login_required
@require_http_methods(["POST"])
def delete_all_saved_searches(request):
    """
    Deletes all the search queries that have been saved for a logged-in user.
    """
    
    # If the user is Anonymous, redirect them to the login view.
    if type(request.user._wrapped) is not User:
        return HttpResponseRedirect(reverse('login'))

    request.user.searches.filter(saved=True).delete()

    return redirect('search_saved')

@login_required
@require_http_methods(["POST"])
def delete_search_object(request, pk):
    next = request.GET.get('next', '')
    instance = SearchQuery.objects.get(pk=pk)
    instance.delete()
    if next == "saved":
        return redirect('search_saved')
    
    return redirect('search_history')