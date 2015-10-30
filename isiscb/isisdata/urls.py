from django.conf.urls import url, include
from haystack.forms import FacetedSearchForm
from haystack.views import FacetedSearchView
from haystack.query import SearchQuerySet
from django.conf.urls import patterns
from isisdata.forms import *
from isisdata.views import IsisSearchView

from . import views

sqs = SearchQuerySet().facet('authors', size=300). \
        facet('type', size=300). \
        facet('publication_date', size=300). \
        facet('persons', size=300). \
        facet('categories', size=300). \
        facet('subjects', size=300). \
        facet('editors', size=300). \
        facet('advisors', size=300). \
        facet('translators', size=300). \
        facet('publishers', size=300). \
        facet('schools', size=300). \
        facet('institutions', size=300). \
        facet('meetings', size=300). \
        facet('periodicals', size=300). \
        facet('book_series', size=300). \
        facet('time_periods', size=300). \
        facet('geographics', size=300). \
        facet('people', size=300). \
        facet('subject_institutions', size=300). \
        facet('serial_publiations', size=300). \
        facet('classification_terms', size=300). \
        facet('concepts', size=300). \
        facet('creative_works', size=300). \
        facet('events', size=300). \
        facet('authority_type', size=300)

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
]
