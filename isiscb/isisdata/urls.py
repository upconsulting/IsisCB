from __future__ import unicode_literals
from django.conf.urls import url, include
from django.views.decorators.cache import cache_page
from haystack.forms import FacetedSearchForm
from haystack.views import FacetedSearchView
from haystack.query import SearchQuerySet

from isisdata.forms import *
from isisdata.views import IsisSearchView
from isisdata.isiscbviews import publicsite_views, authority_views

from . import views
from django.conf import settings

sqs = SearchQuerySet().facet('authors', size=100). \
        facet('type', size=100). \
        facet('publication_date', size=100). \
        facet('persons', size=100). \
        facet('persons_ids', size=100). \
        facet('categories', size=100). \
        facet('subjects', size=100). \
        facet('editors', size=100). \
        facet('advisors', size=100). \
        facet('translators', size=100). \
        facet('publishers', size=100). \
        facet('schools', size=100). \
        facet('institutions', size=100). \
        facet('meetings', size=100). \
        facet('periodicals', size=100). \
        facet('book_series', size=100). \
        facet('time_periods', size=100). \
        facet('geographics', size=100). \
        facet('people', size=100). \
        facet('subject_institutions', size=100). \
        facet('serial_publications', size=100). \
        facet('classification_terms', size=100). \
        facet('concepts', size=100). \
        facet('creative_works', size=100). \
        facet('events', size=100). \
        facet('authority_type', size=100). \
        facet('all_contributor_ids', size=100).\
        facet('subject_ids', size=100). \
        facet('time_period_ids', size=100). \
        facet('geographic_ids'). \
        facet('institution_ids', size=100). \
        facet('publisher_ids', size=100). \
        facet('periodical_ids', size=100).\
        facet('dataset_ids', size=100).\
        facet('concepts_by_subject_ids', size=100).facet('people_by_subject_ids', size=100).\
        facet('institutions_by_subject_ids', size=100).facet('dataset_typed_names', size=100).\
        facet('geocodes').\
        facet('stub_record_status')

urlpatterns = [
    #url(r'^$', views.index, name='index'),
    url(r'^$', IsisSearchView.as_view(form_class=MyFacetedSearchForm, queryset=sqs), name='index'),
    url(r'^$', IsisSearchView.as_view(form_class=MyFacetedSearchForm, queryset=sqs), name='isis-index'),
    url(r'^(?P<obj_id>[A-Z]+[0-9]+)/$', views.index, name='index'),
    url(r'^recent/$', publicsite_views.recent_records, name='recent_records'),
    url(r'^recent/load$', publicsite_views.recent_records_range, name='recent_records_range'),
    url(r'^authority/(?P<authority_id>[A-Z]+[0-9]+)/$', authority_views.authority, name='authority'),
    url(r'^authority/(?P<authority_id>[A-Z]+[0-9]+)/map$', authority_views.get_place_map_data, name='authority_map_data'),
    url(r'^authority/(?P<authority_id>[A-Z]+[0-9]+)/authortimeline$', authority_views.authority_author_timeline, name='authority_author_timeline'),
    url(r'^user/(?P<username>[^/]+)/$', views.user_profile, name='user_profile'),
    url(r'^citation/(?P<citation_id>[A-Z]+[0-9]+)/$', views.citation, name='citation'),
    url(r'^authority/(?P<authority_id>[A-Z]+[0-9]+)\.rdf/$', views.rdf_authority_view, name='authority_rdf'),
    url(r'^citation/(?P<citation_id>[A-Z]+[0-9]+)\.rdf/$', views.rdf_citation_view, name='citation_rdf'),
    url(r'^(?P<base_view>[A-Za-z]+)/(?P<obj_id>[A-Z]+[0-9]+).json$', views.api_redirect),
    url(r'^search/', IsisSearchView.as_view(form_class=MyFacetedSearchForm, queryset=sqs), name='haystack_search'),
    url(r'^unapi/+$', views.unapi_server_root, name='unapi'),
    url(r'^resolver/(?P<citation_id>[A-Z]+[0-9]+)/$', views.get_linkresolver_url, name='linkresolver'),
    url(r'^help', views.help, name='help'),
    url(r'^about', views.about, name='about'),
    url(r'^statistics', views.statistics, name='statistics'),
    url(r'^api', views.api_documentation, name='api'),
    url(r'^(?P<authority_id>[A-Z]+[0-9]+)/timeline/recalculate', authority_views.timeline_recalculate, name='recalculate_timeline'),
    url(r'^curation/', include('curation.urls', namespace="curation")),
]

#if settings.DEBUG:
#    import debug_toolbar
#    urlpatterns = [
#        url('__debug__/', include(debug_toolbar.urls)),
#    ] + urlpatterns
