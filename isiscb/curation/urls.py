from django.conf.urls import include, url

from curation import views


urlpatterns = [
    url(r'^(?i)dashboard/$', views.dashboard, name='dashboard'),
    url(r'^(?i)citation/$', views.citation, name='citation_list'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/$', views.citation, name='curate_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/attribute/$', views.attribute_for_citation, name='create_attribute_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/$', views.attribute_for_citation, name='update_attribute_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/delete/$', views.delete_attribute_for_citation, name='delete_attribute_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/acrelation/$', views.acrelation_for_citation, name='create_acrelation_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/acrelation/(?P<acrelation_id>[A-Z0-9]+)/$', views.acrelation_for_citation, name='update_acrelation_for_citation'),
    # url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/delete/$', views.delete_attribute_for_citation, name='delete_attribute_for_citation'),
    url(r'^(?i)authority/$', views.authority, name='authority_list'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/attribute/$', views.attribute_for_authority, name='create_attribute_for_authority'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/$', views.attribute_for_authority, name='update_attribute_for_authority'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/delete/$', views.delete_attribute_for_authority, name='delete_attribute_for_authority'),
    url(r'^(?i)users/$', views.users, name='user_list'),

    url(r'^(?i)qdsearch/authority/$', views.quick_and_dirty_authority_search, name='quick_and_dirty_authority_search'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/$', views.authority, name='curate_authority'),
]
