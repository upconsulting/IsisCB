from . import views
from isisdata import views as isiscbviews
from isisdata import forms as isiscbforms
from isisdata.isiscbviews import authority_views, citation_views

from django.conf.urls import url

from haystack.forms import FacetedSearchForm
from haystack.views import FacetedSearchView
from haystack.query import SearchQuerySet

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

app_name = "tenants"
urlpatterns = [
    url(r'^(?P<tenant_id>[A-Za-z0-9\-]+)/$', views.home, name='home'),
    url(r'^(?P<tenant_id>[A-Za-z0-9\-]+)/search$', isiscbviews.IsisSearchView.as_view(form_class=isiscbforms.MyFacetedSearchForm, queryset=sqs), name='index'),
    url(r'^(?P<tenant_id>[A-Za-z0-9\-]+)/citation/(?P<citation_id>[A-Z]+[0-9]+)/$', citation_views.citation, name='citation'),
    url(r'^(?P<tenant_id>[A-Za-z0-9\-]+)/authority/$', views.home, name='authority-base'),
    url(r'^(?P<tenant_id>[A-Za-z0-9\-]+)/authority/(?P<authority_id>[A-Za-z]+[0-9]+)/$', authority_views.authority, name='authority'),
    url(r'^(?P<tenant_id>[A-Za-z0-9\-]+)/authority/(?P<authority_id>[A-Za-z]+[0-9]+)/catalog$', authority_views.authority_catalog, name='authority_catalog'),
    url(r'^(?P<tenant_id>[A-Za-z0-9\-]+)/authority/(?P<authority_id>[A-Za-z]+[0-9]+)/authortimeline$', authority_views.authority_author_timeline, name='authority_author_timeline'),
    url(r'^(?P<tenant_id>[A-Za-z0-9\-]+)/help', isiscbviews.help, name='help'),
    url(r'^(?P<tenant_id>[A-Za-z0-9\-]+)/about', isiscbviews.about, name='about'),
    url(r'^(?P<tenant_id>[A-Za-z0-9\-]+)/playground', isiscbviews.playground, name="playground"),
    url(r'^(?P<tenant_id>[A-Za-z0-9\-]+)/graphexplorer', isiscbviews.graph_explorer, name="graph_explorer"),
    url(r'^(?P<tenant_id>[A-Za-z0-9\-]+)/termexplorer', isiscbviews.term_explorer, name="term_explorer"),
    url(r'^(?P<tenant_id>[A-Za-z0-9\-]+)/ngramexplorer', isiscbviews.ngram_explorer, name="ngram_explorer"),

]
