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
from collections import defaultdict, Counter
from urllib.parse import quote
import base64
from operator import itemgetter

from isisdata.models import *
from isisdata.tasks import *
import isisdata.views as isisviews
import isisdata.helpers.isiscb_utils as isiscb_utils

def citation(request, citation_id, tenant_id=None):
    """
    View for individual citation record.
    """
    citation = get_object_or_404(Citation, pk=citation_id)
    
    if not citation.public:
        return HttpResponseForbidden()

    # Some citations are deleted. These should be hidden from public view.
    if citation.status_of_record == Citation.DELETE:
        raise Http404("No such Citation")
    
    context = {}

    authors = citation.acrelation_set.filter(type_controlled__in=[ACRelation.AUTHOR, ACRelation.CONTRIBUTOR, ACRelation.EDITOR], citation__public=True, public=True)
    author_ids = [author.authority.id for author in authors if author.authority]

    subjects = citation.acrelation_set.filter(Q(type_controlled__in=[ACRelation.SUBJECT], citation__public=True, public=True))
    subject_ids = [subject.authority.id for subject in subjects if subject.authority]

    persons = citation.acrelation_set.filter(type_broad_controlled__in=[ACRelation.PERSONAL_RESPONS], citation__public=True, public=True)
    categories = citation.acrelation_set.filter(Q(type_controlled__in=[ACRelation.CATEGORY]), citation__public=True, public=True)

    query_time = Q(type_controlled__in=['TI'], citation__public=True) | (Q(type_controlled__in=[ACRelation.SUBJECT], citation__public=True) & Q(authority__type_controlled__in=[Authority.TIME_PERIOD], citation__public=True))
    time_periods = citation.acrelation_set.filter(query_time).filter(public=True)

    query_places = Q(type_controlled__in=[ACRelation.SUBJECT], citation__public=True) & Q(authority__type_controlled__in=[Authority.GEOGRAPHIC_TERM], citation__public=True)
    places = citation.acrelation_set.filter(query_places).filter(public=True)

    query_concepts = Q(type_controlled__in=[ACRelation.SUBJECT], citation__public=True) & Q(authority__type_controlled__in=[Authority.CONCEPT], citation__public=True)
    concepts = citation.acrelation_set.filter(query_concepts).filter(public=True)

    query_institutions = Q(type_controlled__in=[ACRelation.SUBJECT], citation__public=True) & Q(authority__type_controlled__in=[Authority.INSTITUTION], citation__public=True)
    institutions = citation.acrelation_set.filter(query_institutions).filter(public=True)

    query_people = Q(type_controlled__in=[ACRelation.SUBJECT], citation__public=True) & Q(authority__type_controlled__in=[Authority.PERSON], citation__public=True)
    people = citation.acrelation_set.filter(query_people).filter(public=True)

    tenant = None
    if tenant_id:
        tenant = Tenant.objects.filter(identifier=tenant_id).first()

    # get citations related through CCRelations
    context.update(_get_related_citations(citation_id, tenant, request.include_all_tenants))

    # Similar Citations Generator
    if subjects:
        sqs = SearchQuerySet().models(Citation).facet('all_contributor_ids', size=100). \
                facet('subject_ids', size=100).facet('institution_ids', size=100). \
                facet('geographic_ids', size=1000).facet('time_period_ids', size=100).\
                facet('category_ids', size=100).facet('other_person_ids', size=100).\
                facet('publisher_ids', size=100).facet('periodical_ids', size=100).\
                facet('concepts_by_subject_ids', size=100).facet('people_by_subject_ids', size=100).\
                facet('institutions_by_subject_ids', size=100).facet('dataset_typed_names', size=100).\
                facet('events_timeperiods_ids', size=100).facet('geocodes', size=1000)
        sqs.query.set_limits(low=0, high=20)
        results = sqs.all().exclude(public="false")
        if tenant and not request.include_all_tenants:
            results = results.filter(tenant_ids=tenant.pk)
        similar_citations = results.filter(subject_ids__in=subject_ids).exclude(id=citation_id).query.get_results()
    elif citation.type_controlled not in ['RE']:
        mlt = SearchQuerySet().models(Citation).more_like_this(citation).facet('all_contributor_ids', size=100). \
                facet('subject_ids', size=100).facet('institution_ids', size=100). \
                facet('geographic_ids', size=1000).facet('time_period_ids', size=100).\
                facet('category_ids', size=100).facet('other_person_ids', size=100).\
                facet('publisher_ids', size=100).facet('periodical_ids', size=100).\
                facet('concepts_by_subject_ids', size=100).facet('people_by_subject_ids', size=100).\
                facet('institutions_by_subject_ids', size=100).facet('dataset_typed_names', size=100).\
                facet('events_timeperiods_ids', size=100).facet('geocodes', size=1000)
        mlt.query.set_limits(low=0, high=20)
        if tenant and not request.include_all_tenants:
            mlt = mlt.filter(tenant_ids=tenant_id)
        similar_citations = mlt.all().exclude(public="false").query.get_results()
    else:
        similar_citations = []
        word_cloud_results = EmptySearchQuerySet()

    similar_objects = get_facets_from_citations(similar_citations)

    googleBooksImage = None
    if tenant and tenant.settings.google_api_key:
        googleBooksImage = isisviews.get_google_books_image(citation, False, tenant.settings.google_api_key)

    properties = citation.acrelation_set.exclude(type_controlled__in=[ACRelation.AUTHOR, ACRelation.CONTRIBUTOR, ACRelation.EDITOR, ACRelation.SUBJECT, ACRelation.CATEGORY]).filter(public=True)
    properties_map = defaultdict(list)
    for prop in properties:
        properties_map[prop.type_controlled] += [prop]

    # Location of citation in REST API
    api_view = reverse('citation-detail', args=[citation.id], request=request)

    # Provide progression through search results, if present.

    # make sure we have a session key
    if hasattr(request, 'session') and not request.session.session_key:
        request.session.save()
        request.session.modified = True

    session_id = request.session.session_key
    fromsearch = request.GET.get('fromsearch', False)
    last_query = request.GET.get('last_query', None) 

    query_string = request.GET.get('query_string', None)

    if query_string:
        query_string = quote(query_string) 
        #search_key = base64.b64encode(bytes(last_query, 'utf-8')).decode(errors="ignore")
        search_key = isiscb_utils.generate_search_key(last_query)
    else:
        search_key = None

    user_cache = caches['default']
    search_results = user_cache.get('search_results_citation_' + str(search_key))
    page_citation = user_cache.get(session_id + '_page_citation', None) #request.session.get('page_citation', None)
    if search_results and fromsearch and page_citation:
        search_count = search_results.count()

        prev_search_result = None
        # Only display the "previous" link if we are on page 2+.
        if page_citation > 1:
            prev_search_result = search_results[(page_citation - 1)*20 - 1]

        # If we got to the last result of the previous page we need to count
        #  down the page number.
        if prev_search_result == 'isisdata.citation.' + citation_id:
            page_citation = page_citation - 1
            user_cache.set(session_id + '_page_citation', page_citation)
        search_results_page = search_results[(page_citation - 1)*20:page_citation*20 + 2]
        try:
            search_index = search_results_page.index(citation_id) + 1   # +1 for display.
            if search_index == 21:
                user_cache.set(session_id + '_page_citation', page_citation+1)

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

        except (IndexError, ValueError, AssertionError, TypeError):
            search_previous = None
        if search_index:
            search_current = search_index + (20* (page_citation - 1))
        else:
            search_current = None
    else:
        search_index = None
        search_next = None
        search_previous = None
        search_current = None
        search_count = 0

    context.update({
        'citation_id': citation_id,
        'citation': citation,
        'authors': authors,
        'properties_map': properties,
        'subjects': subjects,
        'concepts': concepts,
        'persons': persons,
        'categories': categories,
        'people': people,
        'time_periods': time_periods,
        'places': places,
        'institutions': institutions,
        'source_instance_id': citation_id,
        'source_content_type': ContentType.objects.get(model='citation').id,
        'api_view': api_view,
        'search_results': search_results,
        'search_index': search_index,
        'search_next': search_next,
        'search_previous': search_previous,
        'search_current': search_current,
        'search_count': search_count,
        'fromsearch': fromsearch,
        'last_query': last_query,
        'query_string': query_string,
        'similar_citations': similar_citations,
        'cover_image': googleBooksImage,
        'similar_objects': similar_objects,
        'tenant_id': tenant_id,
    })

    if tenant_id:
        return render(request, 'tenants/citation.html', context)
    return render(request, 'isisdata/citation.html', context)

def _get_related_citations(citation_id, tenant, include_all_projects):
    related_citations_ic = CCRelation.objects.filter(subject_id=citation_id, type_controlled=CCRelation.INCLUDES_CHAPTER, object__public=True).filter(public=True)
    related_citations_inv_ic = CCRelation.objects.filter(object_id=citation_id, type_controlled=CCRelation.INCLUDES_CHAPTER, subject__public=True).filter(public=True)
    related_citations_isa = CCRelation.objects.filter(subject_id=citation_id, type_controlled=CCRelation.INCLUDES_SERIES_ARTICLE, object__public=True).filter(public=True)
    related_citations_inv_isa = CCRelation.objects.filter(object_id=citation_id, type_controlled=CCRelation.INCLUDES_SERIES_ARTICLE, subject__public=True).filter(public=True)
    related_citations_rb = CCRelation.objects.filter(subject_id=citation_id, type_controlled=CCRelation.REVIEWED_BY, object__public=True).filter(public=True)
    related_citations_re = CCRelation.objects.filter(subject_id=citation_id, type_controlled=CCRelation.RESPONDS_TO, object__public=True).filter(public=True)
    related_citations_inv_re = CCRelation.objects.filter(object_id=citation_id, type_controlled=CCRelation.RESPONDS_TO, subject__public=True).filter(public=True)
   
    if tenant and not include_all_projects:
        related_citations_ic = related_citations_ic.filter(object__owning_tenant=tenant.id)
        related_citations_inv_ic = related_citations_inv_ic.filter(subject__owning_tenant=tenant.id)
        related_citations_isa = related_citations_isa.filter(object__owning_tenant=tenant.id)
        related_citations_inv_isa = related_citations_inv_isa.filter(subject__owning_tenant = tenant.id)
        related_citations_rb = related_citations_rb.filter(object__owning_tenant=tenant.id)
        related_citations_re = related_citations_re.filter(object__owning_tenant=tenant.id)
        related_citations_inv_re = related_citations_inv_re.filter(subject__owning_tenant=tenant.id)

    # review of relations can either be "review of" or "review by"
    if tenant and not include_all_projects:
        ro_query = Q(subject_id=citation_id, type_controlled=CCRelation.REVIEW_OF, object__public=True, object__owning_tenant=tenant.id) | Q(object_id=citation_id, type_controlled=CCRelation.REVIEWED_BY, subject__public=True, subject__owning_tenant=tenant.id)
    else:
        ro_query = Q(subject_id=citation_id, type_controlled=CCRelation.REVIEW_OF, object__public=True) | Q(object_id=citation_id, type_controlled=CCRelation.REVIEWED_BY, subject__public=True)
    related_citations_ro = CCRelation.objects.filter(ro_query).filter(public=True)

    # associated with relations can be in both directions
    if tenant and not include_all_projects:
        as_query = Q(subject_id=citation_id, type_controlled=CCRelation.ASSOCIATED_WITH, object__public=True, object__owning_tenant=tenant.id) | Q(object_id=citation_id, type_controlled=CCRelation.ASSOCIATED_WITH, subject__public=True, subject__owning_tenant=tenant.id)
    else:
        as_query = Q(subject_id=citation_id, type_controlled=CCRelation.ASSOCIATED_WITH, object__public=True) | Q(object_id=citation_id, type_controlled=CCRelation.ASSOCIATED_WITH, subject__public=True)
    related_citations_as = CCRelation.objects.filter(as_query).filter(public=True)

    return {
        'related_citations_ic': related_citations_ic,
        'related_citations_inv_ic': related_citations_inv_ic,
        'related_citations_rb': related_citations_rb,
        'related_citations_isa': related_citations_isa,
        'related_citations_inv_isa': related_citations_inv_isa,
        'related_citations_ro': related_citations_ro,
        'related_citations_re': related_citations_re,
        'related_citations_inv_re': related_citations_inv_re,
        'related_citations_as': related_citations_as,
    }

def get_facets_from_citations(citations):
    objects = defaultdict(list)

    if citations:
        citations_ids = [citation.id for citation in citations]
        citations_qs = Citation.objects.all().filter(id__in=citations_ids)
        acrelations = [acr for citation in citations_qs for acr in citation.acrelations.all()]
        for acrelation in acrelations:
            if acrelation.type_broad_controlled in [acrelation.PERSONAL_RESPONS, acrelation.INSTITUTIONAL_HOST, acrelation.PUBLICATION_HOST]:
                objects[acrelation.type_broad_controlled].append(acrelation.authority)
            if acrelation.type_broad_controlled == acrelation.SUBJECT_CONTENT and acrelation.authority and acrelation.authority.type_controlled:
                objects[acrelation.authority.type_controlled].append(acrelation.authority)

    if objects:
        objects = generate_facets(objects)

    return objects

def generate_facets(objects):
    for key in objects:
        authorities_count = Counter(objects[key])
        facets = []

        for authority in authorities_count:
            facets.append({'authority':authority, 'count':authorities_count[authority]})
        facets = sorted(facets, key=itemgetter('count'), reverse=True)

        objects[key] = facets

    return objects