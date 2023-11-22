from __future__ import print_function
from __future__ import unicode_literals
from builtins import str
from builtins import range
from django.http import HttpResponse, HttpResponseForbidden, Http404, HttpResponseRedirect, JsonResponse
from django.contrib.admin.views.decorators import user_passes_test
from django.shortcuts import get_object_or_404, render, redirect
from django.core.cache import caches
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.contrib.staticfiles import finders

from django.conf import settings

from rest_framework.reverse import reverse

from haystack.query import EmptySearchQuerySet, SearchQuerySet

from isisdata.models import *
from isisdata.tasks import *
import isisdata.helpers.isiscb_utils as isiscb_utils

import datetime
import pytz
import base64
import csv
import os
import requests

# The following code initializes two maps:
#  - one that maps two letter country codes (e.g. DE, US) to three letter country codes (e.g. DEU, USA)
#  - and one that maps three letter country codes to country names
# this is needed for the map on authority pages (IEXP-255)
country_code_map = {}
name_map = {}
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../countryCode.csv'), newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        country_code_map[row['code2']] = row['code3']
        name_map[row['code2']] = row['Name']

def authority_catalog(request, authority_id, tenant_id=None):
    """
    View for individual Authority entries.
    """

    authority = get_object_or_404(Authority, pk=authority_id)

    redirect_from = _get_redirect_from(authority, request)

    redirect = _handle_authority_redirects(authority)
    if redirect:
        return redirect
    
    tenant = None
    if tenant_id:
        tenant = Tenant.objects.filter(identifier=tenant_id).first()

    context = _find_related_citations(authority, tenant.id, request.include_all_tenants)

    # Location of authority in REST API
    api_view = reverse('authority-detail', args=[authority.id], request=request)

    # get related citations and counts
    sqs, search_results = _get_word_cloud_results(authority.id, tenant.id, request.include_all_tenants)
    related_citations_count = search_results.count()
    
    author_contributor_qs = sqs.filter_or(author_ids=authority_id).filter_or(contributor_ids=authority_id) \
            .filter_or(editor_ids=authority_id).filter_or(advisor_ids=authority_id).filter_or(translator_ids=authority_id)
    author_contributor_count = _get_count(author_contributor_qs, authority_id, tenant.id, request.include_all_tenants)

    publisher_qs = sqs.filter_or(publisher_ids=authority_id).filter_or(periodical_ids=authority_id)
    publisher_count = _get_count(publisher_qs,  authority_id, tenant.id, request.include_all_tenants)
    
    subject_category_qs = sqs.filter_or(subject_ids=authority_id).filter_or(category_ids=authority_id)
    subject_category_count = _get_count(subject_category_qs, authority_id, tenant.id, request.include_all_tenants )

    display_type = _get_display_type(authority, author_contributor_count, publisher_count, related_citations_count)

    context.update(_create_facets(search_results, authority_id))

    # gets featured image and synopsis of authority from wikipedia
    wikipedia_data = WikipediaData.objects.filter(authority__id=authority.id).first()
    wikiImage = wikipedia_data.img_url if wikipedia_data and wikipedia_data.img_url else ''
    wikiCredit = wikipedia_data.credit if wikipedia_data and wikipedia_data.credit else ''
    wikiIntro = wikipedia_data.intro if wikipedia_data and wikipedia_data.intro else ''

    # Provide progression through search results, if present.
    last_query = request.GET.get('last_query', None) #request.session.get('last_query', None)
    query_string = request.GET.get('query_string', None)
    fromsearch = request.GET.get('fromsearch', False)
    if query_string:
        query_string = query_string.encode('ascii','ignore')
        #search_key = base64.b64encode(query_string)
        search_key = isiscb_utils.generate_search_key(last_query)
    else:
        search_key = None
    
    # This is the database cache.
    user_cache = caches['default']
    search_results = user_cache.get('search_results_authority_' + str(search_key))
    
    # make sure we have a session key
    if hasattr(request, 'session') and not request.session.session_key:
        request.session.save()
        request.session.modified = True

    session_id = request.session.session_key
    page_authority = user_cache.get(session_id + '_page_authority', None)

    if search_results and fromsearch and page_authority:
        search_count = search_results.count()
        prev_search_result = None
        if (page_authority > 1):
            prev_search_result = search_results[(page_authority - 1)*20 - 1]

        # if we got to the last result of the previous page we need to count down the page number
        if prev_search_result == 'isisdata.authority.' + authority_id:
            page_authority = page_authority - 1
            user_cache.set(session_id + '_page_authority', page_authority)

        search_results_page = search_results[(page_authority - 1)*20:page_authority*20 + 2]

        try:
            search_index = search_results_page.index('isisdata.authority.' + authority_id) + 1   # +1 for display.
            if search_index == 21:
                user_cache.set(session_id + '_page_authority', page_authority+1)

        except (IndexError, ValueError):
            search_index = None
        try:
            search_next = search_results_page[search_index]
        except (IndexError, ValueError, TypeError):
            search_next = None
        try:
            search_previous = search_results_page[search_index - 2]
            if search_index - 2 == -1:
                search_previous = prev_search_result

        # !! Why are we catching all of these errors?
        except (IndexError, ValueError, AssertionError, TypeError):
            search_previous = None
        if search_index:
            search_current = search_index + (20* (page_authority - 1))
        else:
            search_current = None
    else:
        search_index = None
        search_next = None
        search_previous = None
        search_current = None
        search_count = None

    context.update({
        'authority_id': authority_id,
        'authority': authority,
        'display_type': display_type,
        'related_citations_count': related_citations_count,
        'author_contributor_count': author_contributor_count,
        'publisher_count': publisher_count,
        'source_instance_id': authority_id,
        'subject_category_count': subject_category_count,
        'source_content_type': ContentType.objects.get(model='authority').id,
        'api_view': api_view,
        'redirect_from': redirect_from,
        'search_results': search_results,
        'search_index': search_index,
        'search_next': search_next,
        'search_previous': search_previous,
        'search_current': search_current,
        'search_count': search_count,
        'fromsearch': fromsearch,
        'last_query': last_query,
        'query_string': query_string,
        'url_linked_data_name': settings.URL_LINKED_DATA_NAME,
        'wikiIntro': wikiIntro,
        'wikiImage': wikiImage,
        'wikiCredit': wikiCredit,
        'tenant_id': tenant_id,
    })

    if tenant_id:
        return render(request, 'tenants/authority_catalog.html', context)
    return render(request, 'isisdata/authority_catalog.html', context)

def _get_count(queryset, authority_id, tenant_id, include_all_tenants):
    queryset = queryset.exclude(public="false")
    if tenant_id and not include_all_tenants:
        queryset = queryset.filter(owning_tenant=tenant_id)
    return queryset.count()

def _find_related_citations(authority, tenant_id, include_all_tenants):
    show_nr = 3
    acrelation_qs = ACRelation.objects.filter(public=True)

    def _filter_by_tenant(ac_qs):
        if tenant_id and not include_all_tenants:
            return ac_qs.filter(citation__owning_tenant=tenant_id)
        return ac_qs

    related_citations_author = acrelation_qs.filter(authority=authority, type_controlled__in=['AU'], citation__public=True)
    related_citations_author = _filter_by_tenant(related_citations_author)
    related_citations_author = related_citations_author.order_by('-citation__publication_date')[:show_nr]

    related_citations_author_count = acrelation_qs.filter(authority=authority, type_controlled__in=['AU'], citation__public=True)
    related_citations_author_count = _filter_by_tenant(related_citations_author_count)
    related_citations_author_count = related_citations_author_count.values('citation_id').distinct('citation_id')\
                                                  .count()

    related_citations_editor = acrelation_qs.filter(authority=authority, type_controlled__in=['ED'], citation__public=True)
    related_citations_editor = _filter_by_tenant(related_citations_editor)
    related_citations_editor = related_citations_editor .order_by('-citation__publication_date')[:show_nr]

    related_citations_editor_count = acrelation_qs.filter(authority=authority, type_controlled__in=['ED'], citation__public=True)
    related_citations_editor_count = _filter_by_tenant(related_citations_editor_count)
    related_citations_editor_count = related_citations_editor_count.values('citation_id').distinct('citation_id')\
                                                  .count()

    related_citations_advisor = acrelation_qs.filter(authority=authority, type_controlled__in=['AD'], citation__public=True)
    related_citations_advisor = _filter_by_tenant(related_citations_advisor)
    related_citations_advisor = related_citations_advisor.order_by('-citation__publication_date')[:show_nr]

    related_citations_advisor_count = acrelation_qs.filter(authority=authority, type_controlled__in=['AD'], citation__public=True)
    related_citations_advisor_count = _filter_by_tenant(related_citations_advisor_count)
    related_citations_advisor_count = related_citations_advisor_count.values('citation_id').distinct('citation_id')\
                                             .count()

    related_citations_contributor = acrelation_qs.filter(authority=authority, type_controlled__in=['CO'], citation__public=True)
    related_citations_contributor = _filter_by_tenant(related_citations_contributor)
    related_citations_contributor = related_citations_contributor.order_by('-citation__publication_date')[:show_nr]
    
    related_citations_contributor_count = acrelation_qs.filter(authority=authority, type_controlled__in=['CO'], citation__public=True)
    related_citations_contributor_count = _filter_by_tenant(related_citations_contributor_count)
    related_citations_contributor_count = related_citations_contributor_count.values('citation_id').distinct('citation_id')\
                                                               .count()

    related_citations_translator = acrelation_qs.filter(authority=authority, type_controlled__in=['TR'], citation__public=True)
    related_citations_translator = _filter_by_tenant(related_citations_translator)
    related_citations_translator = related_citations_translator.order_by('-citation__publication_date')[:show_nr]
    
    related_citations_translator_count = acrelation_qs.filter(authority=authority, type_controlled__in=['TR'], citation__public=True)
    related_citations_translator_count = _filter_by_tenant(related_citations_translator_count)
    related_citations_translator_count = related_citations_translator_count.values('citation_id').distinct('citation_id')\
                                                .count()

    related_citations_subject = acrelation_qs.filter(authority=authority, type_controlled__in=['SU'], citation__public=True)
    related_citations_subject = _filter_by_tenant(related_citations_subject)
    related_citations_subject = related_citations_subject.order_by('-citation__publication_date')[:show_nr]

    related_citations_subject_count = acrelation_qs.filter(authority=authority, type_controlled__in=['SU'], citation__public=True)
    related_citations_subject_count = _filter_by_tenant(related_citations_subject_count)
    related_citations_subject_count = related_citations_subject_count.values('citation_id').distinct('citation_id')\
                                                   .count()

    related_citations_category = acrelation_qs.filter(authority=authority, type_controlled__in=['CA'], citation__public=True)
    related_citations_category = _filter_by_tenant(related_citations_category)
    related_citations_category = related_citations_category.order_by('-citation__publication_date')[:show_nr]

    related_citations_category_count = acrelation_qs.filter(authority=authority, type_controlled__in=['CA'], citation__public=True)
    related_citations_category_count = _filter_by_tenant(related_citations_category_count)
    related_citations_category_count = related_citations_category_count.values('citation_id').distinct('citation_id')\
                                                    .count()

    related_citations_publisher = acrelation_qs.filter(authority=authority, type_controlled__in=['PU'], citation__public=True)
    related_citations_publisher = _filter_by_tenant(related_citations_publisher)
    related_citations_publisher = related_citations_publisher.order_by('-citation__publication_date')[:show_nr]

    related_citations_publisher_count = acrelation_qs.filter(authority=authority, type_controlled__in=['PU'], citation__public=True)
    related_citations_publisher_count = _filter_by_tenant(related_citations_publisher_count)
    related_citations_publisher_count = related_citations_publisher_count.values('citation_id').distinct('citation_id')\
                                                     .count()

    related_citations_school = acrelation_qs.filter(authority=authority, type_controlled__in=['SC'], citation__public=True)
    related_citations_school = _filter_by_tenant(related_citations_school)
    related_citations_school = related_citations_school.order_by('-citation__publication_date')[:show_nr]

    related_citations_school_count = acrelation_qs.filter(authority=authority, type_controlled__in=['SC'], citation__public=True)
    related_citations_school_count = _filter_by_tenant(related_citations_school_count)
    related_citations_school_count = related_citations_school_count.values('citation_id').distinct('citation_id')\
                                                  .count()

    related_citations_institution = acrelation_qs.filter(authority=authority, type_controlled__in=['IN'], citation__public=True)
    related_citations_institution = _filter_by_tenant(related_citations_institution)
    related_citations_institution = related_citations_institution.order_by('-citation__publication_date')[:show_nr]
    
    related_citations_institution_count = acrelation_qs.filter(authority=authority, type_controlled__in=['IN'], citation__public=True)
    related_citations_institution_count = _filter_by_tenant(related_citations_institution_count)
    related_citations_institution_count = related_citations_institution_count.values('citation_id').distinct('citation_id')\
                                                       .count()

    related_citations_meeting = acrelation_qs.filter(authority=authority, type_controlled__in=['ME'], citation__public=True)
    related_citations_meeting = _filter_by_tenant(related_citations_meeting)
    related_citations_meeting = related_citations_meeting.order_by('-citation__publication_date')[:show_nr]
    
    related_citations_meeting_count = acrelation_qs.filter(authority=authority, type_controlled__in=['ME'], citation__public=True)
    related_citations_meeting_count = _filter_by_tenant(related_citations_meeting_count)
    related_citations_meeting_count = related_citations_meeting_count.values('citation_id').distinct('citation_id')\
                                                   .count()

    related_citations_periodical = acrelation_qs.filter(authority=authority, type_controlled__in=['PE'], citation__public=True)
    related_citations_periodical = _filter_by_tenant(related_citations_periodical)
    related_citations_periodical = related_citations_periodical.order_by('-citation__publication_date')[:show_nr]
    
    related_citations_periodical_count = acrelation_qs.filter(authority=authority, type_controlled__in=['PE'], citation__public=True)
    related_citations_periodical_count = _filter_by_tenant(related_citations_periodical_count)
    related_citations_periodical_count = related_citations_periodical_count.values('citation_id').distinct('citation_id')\
                                                      .count()

    related_citations_book_series = acrelation_qs.filter(authority=authority, type_controlled__in=['BS'], citation__public=True)
    related_citations_book_series = _filter_by_tenant(related_citations_book_series)
    related_citations_book_series = related_citations_book_series.order_by('-citation__publication_date')[:show_nr]
    
    related_citations_book_series_count = acrelation_qs.filter(authority=authority, type_controlled__in=['BS'], citation__public=True)
    related_citations_book_series_count = _filter_by_tenant(related_citations_book_series_count)
    related_citations_book_series_count = related_citations_book_series_count.values('citation_id').distinct('citation_id')\
                                                       .count()
    
    return {
        'related_citations_author': related_citations_author,
        'related_citations_author_count': related_citations_author_count,
        'related_citations_editor': related_citations_editor,
        'related_citations_editor_count': related_citations_editor_count,
        'related_citations_advisor': related_citations_advisor,
        'related_citations_advisor_count': related_citations_advisor_count,
        'related_citations_contributor': related_citations_contributor,
        'related_citations_contributor_count': related_citations_contributor_count,
        'related_citations_translator': related_citations_translator,
        'related_citations_translator_count': related_citations_translator_count,
        'related_citations_subject': related_citations_subject,
        'related_citations_subject_count': related_citations_subject_count,
        'related_citations_category': related_citations_category,
        'related_citations_category_count': related_citations_category_count,
        'related_citations_publisher': related_citations_publisher,
        'related_citations_publisher_count': related_citations_publisher_count,
        'related_citations_school': related_citations_school,
        'related_citations_school_count': related_citations_school_count,
        'related_citations_institution': related_citations_institution,
        'related_citations_institution_count': related_citations_institution_count,
        'related_citations_meeting': related_citations_meeting,
        'related_citations_meeting_count': related_citations_meeting_count,
        'related_citations_periodical': related_citations_periodical,
        'related_citations_periodical_count': related_citations_periodical_count,
        'related_citations_book_series': related_citations_book_series,
        'related_citations_book_series_count': related_citations_book_series_count,
    }

def _create_facets(search_results, authority_id):
    subject_ids_facet = search_results.facet_counts()['fields']['subject_ids'] if 'fields' in search_results.facet_counts() else []
    related_contributors_facet = search_results.facet_counts()['fields']['all_contributor_ids'] if 'fields' in search_results.facet_counts() else []
    related_institutions_facet = search_results.facet_counts()['fields']['institution_ids'] if 'fields' in search_results.facet_counts() else []
    related_geographics_facet = search_results.facet_counts()['fields']['geographic_ids'] if 'fields' in search_results.facet_counts() else []
    related_timeperiod_facet = search_results.facet_counts()['fields']['events_timeperiods_ids'] if 'fields' in search_results.facet_counts() else []
    related_categories_facet = search_results.facet_counts()['fields']['category_ids'] if 'fields' in search_results.facet_counts() else []
    related_other_person_facet = search_results.facet_counts()['fields']['other_person_ids'] if 'fields' in search_results.facet_counts() else []
    related_publisher_facet = search_results.facet_counts()['fields']['publisher_ids'] if 'fields' in search_results.facet_counts() else []
    related_journal_facet = search_results.facet_counts()['fields']['periodical_ids'] if 'fields' in search_results.facet_counts() else []
    related_subject_concepts_facet = search_results.facet_counts()['fields']['concepts_by_subject_ids'] if 'fields' in search_results.facet_counts() else []
    related_subject_people_facet = search_results.facet_counts()['fields']['people_by_subject_ids'] if 'fields' in search_results.facet_counts() else []
    related_subject_institutions_facet = search_results.facet_counts()['fields']['institutions_by_subject_ids'] if 'fields' in search_results.facet_counts() else []
    related_dataset_facet = search_results.facet_counts()['fields']['dataset_typed_names'] if 'fields' in search_results.facet_counts() else []

    # remove current authority from facet results
    subject_ids_facet = _remove_self_from_facets(subject_ids_facet, authority_id)
    related_contributors_facet = _remove_self_from_facets(related_contributors_facet, authority_id)
    related_institutions_facet = _remove_self_from_facets(related_institutions_facet, authority_id)
    related_geographics_facet = _remove_self_from_facets(related_geographics_facet, authority_id)
    related_timeperiod_facet = _remove_self_from_facets(related_timeperiod_facet, authority_id)
    related_categories_facet = _remove_self_from_facets(related_categories_facet, authority_id)
    related_other_person_facet = _remove_self_from_facets(related_other_person_facet, authority_id)
    related_publisher_facet = _remove_self_from_facets(related_publisher_facet, authority_id)
    related_journal_facet = _remove_self_from_facets(related_journal_facet, authority_id)
    related_subject_concepts_facet = _remove_self_from_facets(related_subject_concepts_facet, authority_id)
    related_subject_people_facet = _remove_self_from_facets(related_subject_people_facet, authority_id)
    related_subject_institutions_facet = _remove_self_from_facets(related_subject_institutions_facet, authority_id)
    related_dataset_facet = _remove_self_from_facets(related_dataset_facet, authority_id)

    return {
       'subject_ids_facet': subject_ids_facet,
        'related_contributors_facet': related_contributors_facet,
        'related_institutions_facet': related_institutions_facet,
        'related_geographics_facet': related_geographics_facet,
        'related_timeperiod_facet': related_timeperiod_facet,
        'related_categories_facet': related_categories_facet,
        'related_other_person_facet': related_other_person_facet,
        'related_publisher_facet': related_publisher_facet,
        'related_journal_facet': related_journal_facet,
        'related_subject_concepts_facet': related_subject_concepts_facet,
        'related_subject_people_facet': related_subject_people_facet,
        'related_subject_institutions_facet': related_subject_institutions_facet,
        'related_dataset_facet': related_dataset_facet,
    }

def authority(request, authority_id, tenant_id=None):
    authority = Authority.objects.get(id=authority_id)

    redirect_from = _get_redirect_from(authority, request)

    redirect = _handle_authority_redirects(authority)

    if redirect:
        return redirect
    
    tenant = None
    tenant_id_to_filter = None
    if tenant_id:
        tenant = Tenant.objects.filter(identifier=tenant_id).first()
        if tenant:
            tenant_id_to_filter = tenant.id

     # Location of authority in REST API
    api_view = reverse('authority-detail', args=[authority.id], request=request)

    sqs, related_citations = _get_word_cloud_results(authority.id, tenant_id_to_filter, request.include_all_tenants)

    def filter_by_tenant(sqs, tenant_id):
        """ Method that filters records by tenant if there are any and then returns the count"""
        if tenant_id and not request.include_all_tenants:
            tenant = Tenant.objects.filter(identifier=tenant_id).first()
            sqs = sqs.filter(owning_tenant=tenant.pk)
        return sqs
    
    related_citations = filter_by_tenant(related_citations.order_by('-publication_date_for_sort'), tenant_id)
    
    related_geographics_facet = related_citations.facet_counts()['fields']['geographic_ids'] if 'fields' in related_citations.facet_counts() else []
    related_geographics_facet = _remove_self_from_facets(related_geographics_facet, authority_id)
    
    # count related citations
    related_citations_count = filter_by_tenant(related_citations, tenant_id).count()

    # count citations with this authority as subject
    subject_category_sqs = sqs.all().exclude(public="false").filter_or(subject_ids=authority_id).filter_or(category_ids=authority_id)
    subject_category_count = filter_by_tenant(subject_category_sqs, tenant_id).count()
    
    # count citations with this authority as contributor
    author_contributor_sqs = sqs.all().exclude(public="false").filter_or(author_ids=authority_id).filter_or(contributor_ids=authority_id) \
            .filter_or(editor_ids=authority_id).filter_or(advisor_ids=authority_id).filter_or(translator_ids=authority_id)
    author_contributor_count = filter_by_tenant(author_contributor_sqs, tenant_id).count()
    
    # count citations with this tenant as publisher
    publisher_sqs = sqs.all().exclude(public="false").filter_or(publisher_ids=authority_id)
    publisher_count = filter_by_tenant(publisher_sqs, tenant_id).count()

    display_type = _get_display_type(authority, author_contributor_count, publisher_count, related_citations_count)

    page_number = request.GET.get('page_citation', 1)
    paginator = Paginator(related_citations, 20)
    page_results = paginator.get_page(page_number)

    # gets featured image and synopsis of authority from wikipedia
    wikiImage, wikiIntro, wikiCredit = _get_wikipedia_image_synopsis(authority, author_contributor_count, related_citations_count)

    context = {
        'authority_id': authority_id,
        'authority': authority,
        'source_instance_id': authority_id,
        'source_content_type': ContentType.objects.get(model='authority').id,
        'display_type': display_type,
        'related_citations_count': related_citations_count,
        'api_view': api_view,
        'redirect_from': redirect_from,
        'url_linked_data_name': settings.URL_LINKED_DATA_NAME,
        'wikiIntro': wikiIntro,
        'wikiImage': wikiImage,
        'wikiCredit': wikiCredit,
        'page_results': page_results,
        'related_geographics_facet': related_geographics_facet,
        'author_contributor_count': author_contributor_count,
        'publisher_count': publisher_count,
        'subject_category_count': subject_category_count,
        'tenant_id': tenant_id,
    }

    if tenant_id:
        return render(request, 'tenants/authority.html', context)
    return render(request, 'isisdata/authority.html', context)

def _get_word_cloud_results(authority_id, tenant_id, include_all_tenants):
    # boxes
    sqs = SearchQuerySet().models(Citation).facet('all_contributor_ids', size=100). \
                facet('subject_ids', size=100).facet('institution_ids', size=100). \
                facet('geographic_ids', size=1000).facet('time_period_ids', size=100).\
                facet('category_ids', size=100).facet('other_person_ids', size=100).\
                facet('publisher_ids', size=100).facet('periodical_ids', size=100).\
                facet('concepts_by_subject_ids', size=100).facet('people_by_subject_ids', size=100).\
                facet('institutions_by_subject_ids', size=100).facet('dataset_typed_names', size=100).\
                facet('events_timeperiods_ids', size=100).facet('geocodes', size=1000)
   
    word_cloud_results = sqs.all()
    word_cloud_results = word_cloud_results.filter_or(author_ids=authority_id).filter_or(contributor_ids=authority_id) \
            .filter_or(editor_ids=authority_id).filter_or(subject_ids=authority_id).filter_or(institution_ids=authority_id) \
            .filter_or(category_ids=authority_id).filter_or(advisor_ids=authority_id).filter_or(translator_ids=authority_id) \
            .filter_or(publisher_ids=authority_id).filter_or(school_ids=authority_id).filter_or(meeting_ids=authority_id) \
            .filter_or(periodical_ids=authority_id).filter_or(book_series_ids=authority_id).filter_or(time_period_ids=authority_id) \
            .filter_or(geographic_ids=authority_id).filter_or(about_person_ids=authority_id).filter_or(other_person_ids=authority_id)
    word_cloud_results = word_cloud_results.all().exclude(public="false")
    if tenant_id and not include_all_tenants:
        word_cloud_results = word_cloud_results.filter(owning_tenant=tenant_id)
        #sqs = sqs.filter(owning_tenant=tenant_id)

         
    return sqs, word_cloud_results

def _get_display_type(authority, author_contributor_count, publisher_count, related_citations_count):
    if authority.type_controlled == authority.PERSON and author_contributor_count != 0 and related_citations_count !=0 and author_contributor_count/related_citations_count > .9:
        return 'Author'
    elif authority.type_controlled == authority.INSTITUTION and publisher_count != 0 and related_citations_count !=0 and publisher_count/related_citations_count > .9:
        return 'Publisher'
    else:
        return authority.get_type_controlled_display

def _remove_self_from_facets(facet, authority_id):
        return [x for x in facet if x[0].upper() != authority_id.upper()]

def _get_wikipedia_image_synopsis(authority, author_contributor_count, related_citations_count):
    wikiImage = wikiCredit = wikiIntro = ''

    if not authority.type_controlled == authority.SERIAL_PUBLICATION and not(authority.type_controlled == authority.PERSON and author_contributor_count != 0 and related_citations_count > 0 and author_contributor_count/related_citations_count > .9):
        wikipedia_data = WikipediaData.objects.filter(authority__id=authority.id).first()

        if wikipedia_data and (datetime.datetime.now(datetime.timezone.utc) - wikipedia_data.last_modified).days < settings.WIKIPEDIA_REFRESH_TIME:
            wikiImage = wikipedia_data.img_url
            wikiCredit = wikipedia_data.credit
            wikiIntro = wikipedia_data.intro

        else:
            authorityName = authority.name
            if hasattr(authority, 'person'):
                if authorityName.find(',') >= 0:
                    firstName = authorityName[authorityName.index(',')+1:len(authorityName)].strip()
                    if firstName.find(',') >= 0:
                        firstName = firstName[:firstName.find(',')].strip()
                    lastName = authorityName[:authorityName.find(',')].strip()
                    authorityName = firstName + ' ' + lastName
            elif authority.type_controlled == authority.CONCEPT:
                if authorityName.find(';') >= 0:
                    authorityName = authorityName[:authorityName.find(';')].strip()
            elif authority.type_controlled == authority.GEOGRAPHIC_TERM:
                if authorityName.find('(') >= 0:
                    authorityName = authorityName[:authorityName.find('(')].strip()

            if authorityName:
                imgURL = settings.WIKIPEDIA_IMAGE_API_PATH.format(authorityName = authorityName)
                introURL = settings.WIKIPEDIA_INTRO_API_PATH.format(authorityName = authorityName)
                imgJSON = requests.get(imgURL).json()

                if list(imgJSON['query']['pages'].items())[0][0] != '-1':
                    imgPage = list(imgJSON['query']['pages'].items())[0][1]
                    imgPageID = imgPage['pageid']
                    wikiCredit = f'{settings.WIKIPEDIA_PAGE_PATH}{imgPageID}'
                    if imgPage.get('original') and imgPage['original'].get('source'):
                        wikiImage = imgPage['original']['source']

                    introJSON = requests.get(introURL).json()
                    extract = list(introJSON['query']['pages'].items())[0][1]['extract']
                    if extract.find('may refer to') < 0:
                        wikiIntro = extract

            wikipedia_data = WikipediaData(img_url=wikiImage, credit=wikiCredit, intro=wikiIntro, authority_id=authority.id)
            wikipedia_data.save()

    return wikiImage, wikiIntro, wikiCredit

def get_place_map_data(request, authority_id, tenant_id=None):
    include_all_tenants = request.include_all_tenants if request.include_all_tenants else False
    tenant = None
    if tenant_id:
        tenant = Tenant.objects.filter(identifier=tenant_id).first()

    sqs =SearchQuerySet().models(Citation).facet('geographic_ids', size=1000).facet('geocodes', size=1000)
    map_search_results = sqs.all().exclude(public="false").filter_or(author_ids=authority_id).filter_or(contributor_ids=authority_id) \
            .filter_or(editor_ids=authority_id).filter_or(subject_ids=authority_id).filter_or(institution_ids=authority_id) \
            .filter_or(category_ids=authority_id).filter_or(advisor_ids=authority_id).filter_or(translator_ids=authority_id) \
            .filter_or(publisher_ids=authority_id).filter_or(school_ids=authority_id).filter_or(meeting_ids=authority_id) \
            .filter_or(periodical_ids=authority_id).filter_or(book_series_ids=authority_id).filter_or(time_period_ids=authority_id) \
            .filter_or(geographic_ids=authority_id).filter_or(about_person_ids=authority_id).filter_or(other_person_ids=authority_id)
    if tenant_id and not include_all_tenants:
        map_search_results = map_search_results.filter(owning_tenant=tenant_id)

    related_geographics_facet = map_search_results.facet_counts()['fields']['geographic_ids'] if 'fields' in map_search_results.facet_counts() else []
    geocodes = map_search_results.facet_counts()['fields']['geocodes'] if 'fields' in map_search_results.facet_counts() else []
    citation_count = _get_citation_count_per_country(geocodes)
    country_map_data, country_name_map, is_mapped_map = _get_authority_places_map_data(related_geographics_facet)

    labels = ['<b>{}</b><br>Citations: {}<br>Hits: {}<extra></extra>'.format(country_name_map.get(code, ''), citation_count.get(code,''), country_map_data.get(code, '')) for code in country_name_map.keys()]
    # we need a map in the front end that maps three to two letter codes (USA to US for example)
    # as the map needs three letter codes, but we have two letter codes indexed
    two_letter_codes = { k : list(country_code_map.keys())[list(country_code_map.values()).index(k)] for k in list(country_map_data.keys())}
    return JsonResponse({
        'citation_count_countries': list(citation_count.keys()),
        'citation_count': list(citation_count.values()),
        'countries': list(country_map_data.keys()),
        'map_data': list(country_map_data.values()),
        'labels': labels,
        'name_map': list(country_name_map.values()),
        'two_letter_codes': two_letter_codes,
        'is_mapped_map': is_mapped_map
    })

def _get_citation_count_per_country(facets):
    country_map = {}
    for facet in facets:
        if facet[0] in country_code_map:
            country_map[country_code_map[facet[0]]] = facet[1]
    return country_map

def _get_authority_places_map_data(facets):
    country_map = {}
    country_name_map = {}

    ids = [f[0] for f in facets]
    is_mapped_map = {}
    facets_dict = dict(facets)
    authority_ids = Authority.objects.filter(pk__in=ids, attributes__type_controlled__name=settings.COUNTRY_CODE_ATTRIBUTE).values_list('id').distinct()
    for id in authority_ids:
        country_attrs = Attribute.objects.filter(source_instance_id=id[0], type_controlled__name=settings.COUNTRY_CODE_ATTRIBUTE)
        is_mapped_map[id[0]] = True if country_attrs else False
        for attr in country_attrs:
            attr_value = attr.value.display
            attr_value_list = attr_value.split(",")
            for code_two_letters in attr_value_list:
                if not code_two_letters in country_code_map:
                    continue

                code_two_letters = code_two_letters.strip()
                code_three_letters = country_code_map[code_two_letters]
                country_name_map[code_three_letters] = name_map[code_two_letters]
                if code_three_letters in country_map:
                    country_map[code_three_letters] = country_map[code_three_letters] + facets_dict[id[0]]
                else:
                    country_map[code_three_letters] = facets_dict[id[0]]

    return country_map, country_name_map, is_mapped_map

def _get_redirect_from(authority, request):
    # Some authority entries are deleted. These should be hidden from public
    #  view.
    if authority.record_status_value == CuratedMixin.INACTIVE or (authority.record_status == Authority.DELETE and not authority.record_status_value):
        raise Http404("No such Authority")

    # If the user has been redirected from another Authority entry, this should
    #  be indicated in the view.
    redirect_from_id = request.GET.get('redirect_from')
    if redirect_from_id:
        redirect_from = Authority.objects.get(pk=redirect_from_id)
    else:
        redirect_from = None

    return redirect_from

def _handle_authority_redirects(authority):
    # There are several authority entries that redirect to other entries,
    #  usually because the former is a duplicate of the latter.
    if (authority.record_status == Authority.REDIRECT or authority.record_status_value == CuratedMixin.REDIRECT) and authority.redirect_to is not None:
        redirect_kwargs = {'authority_id': authority.redirect_to.id}
        base_url = reverse('authority', kwargs=redirect_kwargs)
        redirect_url = base_url + '?redirect_from={0}'.format(authority.id)
        return HttpResponseRedirect(redirect_url)

    if not authority.public:
        return HttpResponseForbidden()

def authority_author_timeline(request, authority_id, tenant_id=None):
    now = datetime.datetime.now()

    include_all_tenants = request.include_all_tenants if request.include_all_tenants else False
    tenant = None
    if tenant_id:
        tenant = Tenant.objects.filter(identifier=tenant_id).first()

    tenant_id_to_filter = None
    if tenant and not include_all_tenants:
        tenant_id_to_filter = tenant.id
        cached_timelines = CachedTimeline.objects.filter(authority_id=authority_id, owning_tenant=tenant_id_to_filter).order_by('-created_at')
    else:
        cached_timelines = CachedTimeline.objects.filter(authority_id=authority_id, owning_tenant__isnull=True).order_by('-created_at')
    cached_timeline = cached_timelines[0] if cached_timelines else None
    timeline_to_display = cached_timeline

    # let's show an old one if there is one and current calculation hasn't completed yet
    if cached_timeline and not cached_timeline.complete:
        if len(cached_timelines) > 1:
            timeline_to_display = cached_timelines[1]

    refresh_time = settings.AUTHORITY_TIMELINE_REFRESH_TIME
    data = {}

    # FIXME: there seems to be a bug here. for some reason sometimes this is not true when it should
    timeline_is_outdated = cached_timeline and ((cached_timeline.created_at + datetime.timedelta(hours=refresh_time) < datetime.datetime.now(tz=pytz.utc)) or cached_timeline.recalculate)
    if not cached_timeline or timeline_is_outdated:
        timeline = CachedTimeline()
        timeline.authority_id = authority_id
        if tenant_id_to_filter:
            timeline.owning_tenant = tenant_id_to_filter
        timeline.save()
        create_timeline.apply_async(args=[authority_id, timeline.id, tenant_id_to_filter], queue=settings.CELERY_GRAPH_TASK_QUEUE, routing_key='graph.#')

        data.update({
            'status': 'generating',
        })

    if timeline_to_display:
        if timeline_to_display.complete:
            year_map = { str(year.year) : year for year in timeline_to_display.years.all()}
            years = [year for year in range(1970, now.year+1)]
            book_count = []
            thesis_count = []
            chapter_count = []
            article_count = []
            review_count = []
            other_count = []

            now = datetime.datetime.now()
            titles = {}
            # including the current year
            for running_year in range(1970, now.year+1):
                running_year_str = str(running_year)
                if running_year_str in year_map:
                    year = year_map[running_year_str]
                    book_count.append(year.book_count)
                    thesis_count.append(year.thesis_count)
                    chapter_count.append(year.chapter_count)
                    article_count.append(year.article_count)
                    review_count.append(year.review_count)
                    other_count.append(year.other_count)

                    titles.update({
                        running_year_str: {
                             'books': [title.title for title in year.titles.filter(citation_type=Citation.BOOK)],
                             'theses': [title.title for title in year.titles.filter(citation_type=Citation.THESIS)],
                             'chapters': [title.title for title in year.titles.filter(citation_type=Citation.CHAPTER)],
                             'articles': [title.title for title in year.titles.filter(citation_type=Citation.ARTICLE)],
                             'reviews': [title.title for title in year.titles.filter(citation_type__in=[Citation.REVIEW, Citation.ESSAY_REVIEW])],
                             'others': [title.title for title in year.titles.exclude(citation_type__in=[Citation.BOOK, Citation.THESIS, Citation.CHAPTER, Citation.ARTICLE, Citation.REVIEW, Citation.ESSAY_REVIEW])],
                        }
                    })
                else:
                    book_count.append(0)
                    thesis_count.append(0)
                    chapter_count.append(0)
                    article_count.append(0)
                    review_count.append(0)
                    other_count.append(0)

                    titles.update({
                        running_year_str: {
                             'books': [],
                             'theses': [],
                             'chapters': [],
                             'articles': [],
                             'reviews': [],
                             'others': [],
                        }
                    })

            user_init_refresh_time = settings.AUTHORITY_TIMELINE_REFRESH_TIME_USER_INIT
            can_recalculate = cached_timeline.created_at + datetime.timedelta(hours=user_init_refresh_time) < datetime.datetime.now(tz=pytz.utc)
            data.update({
                'status': 'done',
                'generated_on': timeline_to_display.created_at,
                'timeline_recalculation': 'running' if timeline_to_display.recalculate or timeline_is_outdated else 'none',
                'can_recalculate': can_recalculate,
                'years': years,
                'books': book_count,
                'theses': thesis_count,
                'chapters': chapter_count,
                'articles': article_count,
                'reviews': review_count,
                'others': other_count,
                'titles': titles,
            })
        else:
            data.update({
                'status': 'generating',
            })

    return JsonResponse(data)

@user_passes_test(lambda u: u.is_authenticated)
def timeline_recalculate(request, authority_id, tenant_id=None):
    if (request.method == 'POST'):
        if tenant_id and not request.include_all_tenants:
            tenant = get_object_or_404(Tenant, identifier=tenant_id)
            cached_timeline = CachedTimeline.objects.filter(authority_id=authority_id, owning_tenant=tenant.id).order_by('-created_at').first()
        else:
            cached_timeline = CachedTimeline.objects.filter(authority_id=authority_id, owning_tenant__isnull=True).order_by('-created_at').first()
        refresh_time = settings.AUTHORITY_TIMELINE_REFRESH_TIME_USER_INIT
        if cached_timeline and cached_timeline.created_at + datetime.timedelta(hours=refresh_time) < datetime.datetime.now(tz=pytz.utc):
            cached_timeline.recalculate = True
            cached_timeline.save()

    if tenant_id:
        return HttpResponseRedirect(reverse('tenants:authority', args=[tenant_id, authority_id]))    
    return HttpResponseRedirect(reverse('authority', args=[authority_id]))
