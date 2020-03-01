from django.http import HttpResponse, HttpResponseForbidden, Http404, HttpResponseRedirect, JsonResponse
from django.contrib.admin.views.decorators import user_passes_test
from django.shortcuts import get_object_or_404, render, redirect
from django.core.cache import caches
from django.db.models import Prefetch

from django.conf import settings

from rest_framework.reverse import reverse

from haystack.query import EmptySearchQuerySet, SearchQuerySet

from isisdata.models import *
from isisdata.tasks import *

import datetime
import pytz
import base64

def authority(request, authority_id):
    """
    View for individual Authority entries.
    """

    authority = Authority.objects.get(id=authority_id)

    # Some authority entries are deleted. These should be hidden from public
    #  view.
    if authority.record_status == Authority.DELETE or authority.record_status_value == CuratedMixin.INACTIVE:
        raise Http404("No such Authority")

    # If the user has been redirected from another Authority entry, this should
    #  be indicated in the view.
    redirect_from_id = request.GET.get('redirect_from')
    if redirect_from_id:
        redirect_from = Authority.objects.get(pk=redirect_from_id)
    else:
        redirect_from = None

    # There are several authority entries that redirect to other entries,
    #  usually because the former is a duplicate of the latter.
    if (authority.record_status == Authority.REDIRECT or authority.record_status_value == CuratedMixin.REDIRECT) and authority.redirect_to is not None:
        redirect_kwargs = {'authority_id': authority.redirect_to.id}
        base_url = reverse('authority', kwargs=redirect_kwargs)
        redirect_url = base_url + '?redirect_from={0}'.format(authority.id)
        return HttpResponseRedirect(redirect_url)

    if not authority.public:
        return HttpResponseForbidden()

    show_nr = 3
    acrelation_qs = ACRelation.objects.filter(public=True)
    related_citations_author = acrelation_qs.filter(authority=authority, type_controlled__in=['AU'], citation__public=True)\
                                             .order_by('-citation__publication_date')[:show_nr]
    related_citations_author_count = acrelation_qs.filter(authority=authority, type_controlled__in=['AU'], citation__public=True)\
                                                  .values('citation_id').distinct('citation_id')\
                                                  .count()

    related_citations_editor = acrelation_qs.filter(authority=authority, type_controlled__in=['ED'], citation__public=True)\
                                            .order_by('-citation__publication_date')[:show_nr]
    related_citations_editor_count = acrelation_qs.filter(authority=authority, type_controlled__in=['ED'], citation__public=True)\
                                                  .values('citation_id').distinct('citation_id')\
                                                  .count()

    related_citations_advisor = acrelation_qs.filter(authority=authority, type_controlled__in=['AD'], citation__public=True)\
                                             .order_by('-citation__publication_date')[:show_nr]
    related_citations_advisor_count = acrelation_qs.filter(authority=authority, type_controlled__in=['AD'], citation__public=True)\
                                             .values('citation_id').distinct('citation_id')\
                                             .count()

    related_citations_contributor = acrelation_qs.filter(authority=authority, type_controlled__in=['CO'], citation__public=True)\
                                                 .order_by('-citation__publication_date')[:show_nr]
    related_citations_contributor_count = acrelation_qs.filter(authority=authority, type_controlled__in=['CO'], citation__public=True)\
                                                               .values('citation_id').distinct('citation_id')\
                                                               .count()

    related_citations_translator = acrelation_qs.filter(authority=authority, type_controlled__in=['TR'], citation__public=True)\
                                                .order_by('-citation__publication_date')[:show_nr]
    related_citations_translator_count = acrelation_qs.filter(authority=authority, type_controlled__in=['TR'], citation__public=True)\
                                                .values('citation_id').distinct('citation_id')\
                                                .count()

    related_citations_subject = acrelation_qs.filter(authority=authority, type_controlled__in=['SU'], citation__public=True)\
                                             .order_by('-citation__publication_date')[:show_nr]
    related_citations_subject_count = acrelation_qs.filter(authority=authority, type_controlled__in=['SU'], citation__public=True)\
                                                   .values('citation_id').distinct('citation_id')\
                                                   .count()

    related_citations_category = acrelation_qs.filter(authority=authority, type_controlled__in=['CA'], citation__public=True)\
                                              .order_by('-citation__publication_date')[:show_nr]
    related_citations_category_count = acrelation_qs.filter(authority=authority, type_controlled__in=['CA'], citation__public=True)\
                                                    .values('citation_id').distinct('citation_id')\
                                                    .count()

    related_citations_publisher = acrelation_qs.filter(authority=authority, type_controlled__in=['PU'], citation__public=True)\
                                               .order_by('-citation__publication_date')[:show_nr]
    related_citations_publisher_count = acrelation_qs.filter(authority=authority, type_controlled__in=['PU'], citation__public=True)\
                                                     .values('citation_id').distinct('citation_id')\
                                                     .count()

    related_citations_school = acrelation_qs.filter(authority=authority, type_controlled__in=['SC'], citation__public=True)\
                                            .order_by('-citation__publication_date')[:show_nr]
    related_citations_school_count = acrelation_qs.filter(authority=authority, type_controlled__in=['SC'], citation__public=True)\
                                                  .values('citation_id').distinct('citation_id')\
                                                  .count()

    related_citations_institution = acrelation_qs.filter(authority=authority, type_controlled__in=['IN'], citation__public=True)\
                                                 .order_by('-citation__publication_date')[:show_nr]
    related_citations_institution_count = acrelation_qs.filter(authority=authority, type_controlled__in=['IN'], citation__public=True)\
                                                       .values('citation_id').distinct('citation_id')\
                                                       .count()

    related_citations_meeting = acrelation_qs.filter(authority=authority, type_controlled__in=['ME'], citation__public=True)\
                                             .order_by('-citation__publication_date')[:show_nr]
    related_citations_meeting_count = acrelation_qs.filter(authority=authority, type_controlled__in=['ME'], citation__public=True)\
                                                   .values('citation_id').distinct('citation_id')\
                                                   .count()

    related_citations_periodical = acrelation_qs.filter(authority=authority, type_controlled__in=['PE'], citation__public=True)\
                                                .order_by('-citation__publication_date')[:show_nr]
    related_citations_periodical_count = acrelation_qs.filter(authority=authority, type_controlled__in=['PE'], citation__public=True)\
                                                      .values('citation_id').distinct('citation_id')\
                                                      .count()

    related_citations_book_series = acrelation_qs.filter(authority=authority, type_controlled__in=['BS'], citation__public=True)\
                                                 .order_by('-citation__publication_date')[:show_nr]
    related_citations_book_series_count = acrelation_qs.filter(authority=authority, type_controlled__in=['BS'], citation__public=True)\
                                                       .values('citation_id').distinct('citation_id')\
                                                       .count()

    related_citations_count = acrelation_qs.filter(authority=authority, citation__public=True)\
                                                       .values('citation_id').distinct('citation_id')\
                                                       .count()

    # Location of authority in REST API
    api_view = reverse('authority-detail', args=[authority.id], request=request)

    # WordCloud
    sqs =SearchQuerySet().facet('all_contributor_ids', size=100). \
                facet('subject_ids', size=100).facet('institution_ids', size=100). \
                facet('geographic_ids', size=100).facet('time_period_ids', size=100).\
                facet('category_ids', size=100).facet('other_person_ids', size=100).\
                facet('publisher_ids', size=100).facet('periodical_ids', size=100).\
                facet('concepts_by_subject_ids', size=100).facet('people_by_subject_ids', size=100).\
                facet('institutions_by_subject_ids', size=100)
    word_cloud_results = sqs.all().filter_or(author_ids__eq=authority_id).filter_or(contributor_ids__eq=authority_id) \
            .filter_or(editor_ids__eq=authority_id).filter_or(subject_ids=authority_id).filter_or(institution_ids=authority_id) \
            .filter_or(category_ids=authority_id).filter_or(advisor_ids=authority_id).filter_or(translator_ids=authority_id) \
            .filter_or(publisher_ids=authority_id).filter_or(school_ids=authority_id).filter_or(meeting_ids=authority_id) \
            .filter_or(periodical_ids=authority_id).filter_or(book_series_ids=authority_id).filter_or(time_period_ids=authority_id) \
            .filter_or(geographic_ids=authority_id).filter_or(about_person_ids=authority_id).filter_or(other_person_ids=authority_id) \

    subject_ids_facet = word_cloud_results.facet_counts()['fields']['subject_ids']
    related_contributors_facet = word_cloud_results.facet_counts()['fields']['all_contributor_ids']
    related_institutions_facet = word_cloud_results.facet_counts()['fields']['institution_ids']
    related_geographics_facet = word_cloud_results.facet_counts()['fields']['geographic_ids']
    related_timeperiod_facet = word_cloud_results.facet_counts()['fields']['time_period_ids']
    related_categories_facet = word_cloud_results.facet_counts()['fields']['category_ids']
    related_other_person_facet = word_cloud_results.facet_counts()['fields']['other_person_ids']
    related_publisher_facet = word_cloud_results.facet_counts()['fields']['publisher_ids']
    related_journal_facet = word_cloud_results.facet_counts()['fields']['periodical_ids']
    related_subject_concepts_facet = word_cloud_results.facet_counts()['fields']['concepts_by_subject_ids']
    related_subject_people_facet = word_cloud_results.facet_counts()['fields']['people_by_subject_ids']
    related_subject_institutions_facet = word_cloud_results.facet_counts()['fields']['institutions_by_subject_ids']

    # Provide progression through search results, if present.
    last_query = request.GET.get('last_query', None) #request.session.get('last_query', None)
    query_string = request.GET.get('query_string', None)
    fromsearch = request.GET.get('fromsearch', False)
    if query_string:
        query_string = query_string.encode('ascii','ignore')
        search_key = base64.b64encode(last_query)
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


    context = {
        'authority_id': authority_id,
        'authority': authority,
        'related_citations_count': related_citations_count,
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
        'source_instance_id': authority_id,
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
        'url_linked_data_name': settings.URL_LINKED_DATA_NAME,
    }
    return render(request, 'isisdata/authority.html', context)

def authority_author_timeline(request, authority_id):
    now = datetime.datetime.now()

    cached_timelines = CachedTimeline.objects.filter(authority_id=authority_id).order_by('-created_at')
    cached_timeline = cached_timelines[0] if cached_timelines else None
    timeline_to_display = cached_timeline

    # let's show an old one if there is one and current calculation hasn't completed yet
    if cached_timeline and not cached_timeline.complete:
        if len(cached_timelines) > 1:
            timeline_to_display = cached_timelines[1]

    refresh_time = settings.AUTHORITY_TIMELINE_REFRESH_TIME
    data = {}

    timeline_is_outdated = cached_timeline and ((cached_timeline.created_at + datetime.timedelta(hours=refresh_time) < datetime.datetime.now(tz=pytz.utc)) or cached_timeline.recalculate)
    if not cached_timeline or timeline_is_outdated:
        print "Refreshing timeline for " + authority_id
        timeline = CachedTimeline()
        timeline.authority_id = authority_id
        timeline.save()
        create_timeline.apply_async(args=[authority_id, timeline.id], queue=settings.CELERY_GRAPH_TASK_QUEUE)

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
def timeline_recalculate(request, authority_id):
    if (request.method == 'POST'):
        cached_timeline = CachedTimeline.objects.filter(authority_id=authority_id).order_by('-created_at').first()

        refresh_time = settings.AUTHORITY_TIMELINE_REFRESH_TIME_USER_INIT
        if cached_timeline and cached_timeline.created_at + datetime.timedelta(hours=refresh_time) < datetime.datetime.now(tz=pytz.utc):
            cached_timeline.recalculate = True
            cached_timeline.save()

    return HttpResponseRedirect(reverse('authority', args=[authority_id]))
