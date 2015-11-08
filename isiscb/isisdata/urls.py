from django.conf.urls import url, include
from haystack.forms import FacetedSearchForm
from haystack.views import FacetedSearchView
from haystack.query import SearchQuerySet
from django.conf.urls import patterns
from isisdata.forms import *
from isisdata.views import IsisSearchView

from . import views

sqs = SearchQuerySet().facet('authors', size=100). \
        facet('type', size=100). \
        facet('publication_date', size=100). \
        facet('persons', size=100). \
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
        facet('serial_publiations', size=100). \
        facet('classification_terms', size=100). \
        facet('concepts', size=100). \
        facet('creative_works', size=100). \
        facet('events', size=100). \
        facet('authority_type', size=100)

urlpatterns = [
    #url(r'^$', views.index, name='index'),
    url(r'^$',
        IsisSearchView(form_class=MyFacetedSearchForm, searchqueryset=sqs),
        name='index'),
    url(r'^(?P<obj_id>[A-Z]+[0-9]+)/$', views.index, name='index'),
    url(r'^authority/(?P<authority_id>[A-Z]+[0-9]+)/$',
        views.authority,
        name='authority'),
    url(r'^citation/(?P<citation_id>[A-Z]+[0-9]+)/$',
        views.citation,
        name='citation'),
    url(r'^(?P<base_view>[A-Za-z]+)/(?P<obj_id>[A-Z]+[0-9]+).json$', views.api_redirect),
    url(r'^search/',
        IsisSearchView(form_class=MyFacetedSearchForm, searchqueryset=sqs),
        name='haystack_search'),
    url(r'^unapi/+$', views.unapi_server_root, name='unapi'),
    url(r'^help', views.help, name='help'),
    url(r'^about', views.about, name='about'),
]
