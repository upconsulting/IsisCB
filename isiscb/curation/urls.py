from django.conf.urls import include, url

from curation import views


urlpatterns = [
    url(r'^(?i)dashboard/$', views.dashboard, name='dashboard'),
    url(r'^(?i)citation/$', views.citation, name='citation_list'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/$', views.citation, name='curate_citation'),
    url(r'^(?i)authority/$', views.authority, name='authority_list'),
    url(r'^(?i)users/$', views.users, name='user_list'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/$', views.authority, name='curate_authority'),
    url(r'^(?i)users/role/$', views.add_role, name='create_role'),
]
