from __future__ import unicode_literals
from django.conf.urls import include
from django.urls import re_path
from django.conf.urls.static import static
from django.views.decorators.cache import cache_page
from django.contrib.auth.decorators import login_required
from haystack.forms import FacetedSearchForm
from haystack.views import FacetedSearchView
from haystack.query import SearchQuerySet

from isisdata.forms import *
from isisdata.views import IsisSearchView
from isisdata.isiscbviews import publicsite_views, authority_views, citation_views

from . import views
from django.conf import settings

sqs = SearchQuerySet().facet('authors', size=100). \
        facet('type', size=100). \
        facet('language', size=100). \
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
    #re_path(r'^$', views.index, name='index'),
    re_path(r'^$', login_required(IsisSearchView.as_view(form_class=MyFacetedSearchForm, queryset=sqs)), name='index'),
    re_path(r'^$', login_required(IsisSearchView.as_view(form_class=MyFacetedSearchForm, queryset=sqs)), name='isis-index'),
    re_path(r'^(?P<obj_id>[A-Z]+[0-9]+)/$', views.index, name='index'),
    re_path(r'^recent/$', publicsite_views.recent_records, name='recent_records'),
    re_path(r'^recent/load$', publicsite_views.recent_records_range, name='recent_records_range'),
    re_path(r'^authority/(?P<authority_id>[A-Za-z]+[0-9]+)/$', authority_views.authority, name='authority'),
    re_path(r'^authority/(?P<authority_id>[A-Za-z]+[0-9]+)/map$', authority_views.get_place_map_data, name='authority_map_data'),
    re_path(r'^authority/(?P<authority_id>[A-Za-z]+[0-9]+)/authortimeline$', authority_views.authority_author_timeline, name='authority_author_timeline'),
    re_path(r'^authority/(?P<authority_id>[A-Za-z]+[0-9]+)/catalog$', authority_views.authority_catalog, name='authority_catalog'),
    re_path(r'^citation/(?P<citation_id>[A-Z]+[0-9]+)/$', citation_views.citation, name='citation'),
    re_path(r'^authority/(?P<authority_id>[A-Za-z]+[0-9]+)\.rdf/$', views.rdf_authority_view, name='authority_rdf'),
    re_path(r'^citation/(?P<citation_id>[A-Z]+[0-9]+)\.rdf/$', views.rdf_citation_view, name='citation_rdf'),
    re_path(r'^(?P<base_view>[A-Za-z]+)/(?P<obj_id>[A-Z]+[0-9]+).json$', views.api_redirect),
    re_path(r'^search/', login_required(IsisSearchView.as_view(form_class=MyFacetedSearchForm, queryset=sqs)), name='haystack_search'),
    re_path(r'^unapi/+$', views.unapi_server_root, name='unapi'),
    re_path(r'^resolver/(?P<citation_id>[A-Z]+[0-9]+)/$', views.get_linkresolver_url, name='linkresolver'),
    re_path(r'^help', views.help, name='help'),
    re_path(r'^about', views.about, name='about'),
    re_path(r'^statistics', views.statistics, name='statistics'),
    re_path(r'^api', views.api_documentation, name='api'),
    re_path(r'^(?P<authority_id>[A-Z]+[0-9]+)/timeline/recalculate', authority_views.timeline_recalculate, name='recalculate_timeline'),
    re_path(r'^playground', views.playground, name="playground"),
    re_path(r'^graphexplorer', views.graph_explorer, name="graph_explorer"),
    re_path(r'^termexplorer', views.term_explorer, name="term_explorer"),
    re_path(r'^ngramexplorer', views.ngram_explorer, name="ngram_explorer"),
    re_path(r'^genealogy', views.genealogy, name="genealogy"),
    re_path(r'^theses_by_school', views.theses_by_school, name="theses_by_school"),
    re_path(r'^curation/', include('curation.urls', namespace="curation")),
]



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


#if settings.DEBUG:
#    import debug_toolbar
#    urlpatterns = [
#        re_path('__debug__/', include(debug_toolbar.urls)),
#    ] + urlpatterns
