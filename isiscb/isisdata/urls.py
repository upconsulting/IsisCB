from django.conf.urls import url
from haystack.forms import FacetedSearchForm
from haystack.views import FacetedSearchView
from haystack.query import SearchQuerySet
from django.conf.urls import patterns

from . import views

sqs = SearchQuerySet().facet('authors').facet('subjects')

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^(?P<obj_id>[A-Z]+[0-9]+)/$', views.index, name='index'),
    url(r'^authority/(?P<authority_id>[A-Z]+[0-9]+)/$', views.authority, name='authority'),
    url(r'^citation/(?P<citation_id>[A-Z]+[0-9]+)/$', views.citation, name='citation'),
    url(r'^search/', FacetedSearchView(form_class=FacetedSearchForm, searchqueryset=sqs), name='haystack_search')
]
