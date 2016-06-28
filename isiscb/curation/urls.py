from __future__ import absolute_import

from django.conf.urls import include, url

from curation import views
import rules
from .rules import is_accessible_by_dataset

rules.add_rule('is_accessible_by_dataset',is_accessible_by_dataset)

rules.add_perm('isiscb.view_dataset', is_accessible_by_dataset)

urlpatterns = [
    url(r'^(?i)dashboard/$', views.dashboard, name='dashboard'),
    url(r'^(?i)citation/$', views.citation, name='citation_list'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/$', views.citation, name='curate_citation'),
    url(r'^(?i)authority/$', views.authority, name='authority_list'),
    url(r'^(?i)users/$', views.users, name='user_list'),
    url(r'^(?i)users/addrole/(?P<user_edit_id>[0-9]+)/$', views.add_role_to_user, name='add_role_to_user'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/$', views.authority, name='curate_authority'),
    url(r'^(?i)users/role/$', views.add_role, name='create_role'),
    url(r'^(?i)users/role/(?P<role_id>[0-9]+)/$', views.role, name='role'),
    url(r'^(?i)users/rule/dataset/(?P<role_id>[0-9]+)/$', views.add_dataset_rule, name='create_rule_dataset'),
]
