from django.conf.urls import url, include

from zotero.views import *

urlpatterns = [
    #url(r'^$', views.index, name='index'),
    url(r'suggest/citation/(?P<citation_id>[0-9]+)/$', suggest_citation_json, name='suggest_citation'),
    url(r'suggest/authority/(?P<authority_id>[0-9]+)/$', suggest_authority_json, name='suggest_authority'),
    url(r'suggest/acrelation/(?P<acrelation_id>[0-9]+)/$', suggest_acrelation_json, name='suggest_acrelation'),
    url(r'suggest/acrelation/(?P<acrelation_id>[A-Z]+[0-9]+)/$', suggest_production_acrelation_json, name='suggest_production_acrelation'),
]
