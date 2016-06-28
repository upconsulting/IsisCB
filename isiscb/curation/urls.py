from django.conf.urls import include, url

from curation import views


urlpatterns = [
    url(r'^(?i)dashboard/$', views.dashboard, name='dashboard'),
    url(r'^(?i)citation/$', views.citation, name='citation_list'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/$', views.citation, name='curate_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/attribute/$', views.attribute_for_citation, name='create_attribute_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/$', views.attribute_for_citation, name='update_attribute_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/delete/$', views.delete_attribute_for_citation, name='delete_attribute_for_citation'),
    url(r'^(?i)authority/$', views.authority, name='authority_list'),
    url(r'^(?i)users/$', views.users, name='user_list'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/$', views.authority, name='curate_authority'),
]
