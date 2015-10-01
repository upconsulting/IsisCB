from django.conf.urls import url, include
from haystack.forms import FacetedSearchForm
from haystack.views import FacetedSearchView
from haystack.query import SearchQuerySet
from django.conf.urls import patterns
from isisdata.forms import *
from isisdata.views import IsisSearchView

from . import views

sqs = SearchQuerySet().facet('authors'). \
        facet('type'). \
        facet('persons'). \
        facet('categories'). \
        facet('subjects'). \
        facet('editors'). \
        facet('advisors'). \
        facet('translators'). \
        facet('publishers'). \
        facet('schools'). \
        facet('institutions'). \
        facet('meetings'). \
        facet('periodicals'). \
        facet('book_series'). \
        facet('time_periods'). \
        facet('geographics'). \
        facet('people'). \
        facet('subject_institutions'). \
        facet('serial_publiations'). \
        facet('classification_terms'). \
        facet('concepts'). \
        facet('creative_works'). \
        facet('events')

urlpatterns = [
    #url(r'^$', views.index, name='index'),
    url(r'^$', IsisSearchView(form_class=MyFacetedSearchForm, searchqueryset=sqs), name='index'),
    url(r'^(?P<obj_id>[A-Z]+[0-9]+)/$', views.index, name='index'),
    url(r'^authority/(?P<authority_id>[A-Z]+[0-9]+)/$', views.authority, name='authority'),
    url(r'^citation/(?P<citation_id>[A-Z]+[0-9]+)/$', views.citation, name='citation'),
    url(r'^search/', IsisSearchView(form_class=MyFacetedSearchForm, searchqueryset=sqs), name='haystack_search'),
    url(r'^unapi/+$', views.unapi_server_root, name='unapi'),
]
