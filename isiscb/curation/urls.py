from __future__ import absolute_import

from django.conf.urls import include, url

from curation import views
import rules
from .rules import *

rules.add_rule('is_accessible_by_dataset',is_accessible_by_dataset)
rules.add_rule('can_view_record', can_view_record)
rules.add_rule('can_edit_record', can_edit_record)
rules.add_rule('can_create_record', can_create_record)
rules.add_rule('can_delete_record', can_delete_record)

rules.add_rule('can_view_citation_field', can_view_citation_field & can_view_citation_record_using_id)
rules.add_rule('can_update_citation_field', can_update_citation_field & can_edit_citation_record_using_id)

rules.add_rule('can_view_authority_field', can_view_authority_field & can_view_authority_record_using_id)
rules.add_rule('can_update_authority_field', can_update_authority_field & can_edit_authority_record_using_id)

rules.add_rule('is_user_staff', is_user_staff)
rules.add_rule('is_user_superuser', is_user_superuser)
rules.add_rule('can_view_user_module', can_view_user_module)
rules.add_rule('can_update_user_module', can_update_user_module)

can_access_and_view = is_accessible_by_dataset & can_view_record
rules.add_rule('can_access_and_view', can_access_and_view)

can_access_view_edit = is_accessible_by_dataset & can_view_record & can_edit_record
rules.add_rule('can_access_view_edit', can_access_view_edit)

rules.add_rule('has_zotero_access', has_zotero_access)


urlpatterns = [
    url(r'^(?i)dashboard/$', views.dashboard, name='dashboard'),
    url(r'^(?i)datasets/$', views.datasets, name='datasets'),
    url(r'^(?i)citation/$', views.citations, name='citation_list'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/$', views.citation, name='curate_citation'),

    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/ccrelation/$', views.create_ccrelation_for_citation, name='create_ccrelation_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/ccrelation/(?P<ccrelation_id>[A-Z0-9]+)/$', views.ccrelation_for_citation, name='ccrelation_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/ccrelation/(?P<ccrelation_id>[A-Z0-9]+)/delete/$', views.delete_ccrelation_for_citation, name='delete_ccrelation_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/ccrelation/(?P<ccrelation_id>[A-Z0-9]+)/delete\.(?P<format>[a-z]+)$', views.delete_ccrelation_for_citation, name='delete_ccrelation_for_citation_format'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/language/remove/$', views.delete_language_for_citation, name='delete_language_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/language/add/$', views.add_language_for_citation, name='add_language_for_citation'),


    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/acrelation/$', views.create_acrelation_for_citation, name='create_acrelation_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/acrelation/(?P<acrelation_id>[A-Z0-9]+)/$', views.acrelation_for_citation, name='update_acrelation_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/acrelation/(?P<acrelation_id>[A-Z0-9]+)/delete/$', views.delete_acrelation_for_citation, name='delete_acrelation_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/acrelation/(?P<acrelation_id>[A-Z0-9]+)/delete\.(?P<format>[a-z]+)$', views.delete_acrelation_for_citation, name='delete_acrelation_for_citation_format'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/acrelation/$', views.create_acrelation_for_authority, name='create_acrelation_for_authority'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/acrelation/(?P<acrelation_id>[A-Z0-9]+)/$', views.acrelation_for_authority, name='update_acrelation_for_authority'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/acrelation/(?P<acrelation_id>[A-Z0-9]+)/delete/$', views.delete_acrelation_for_authority, name='delete_acrelation_for_authority'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/acrelation/(?P<acrelation_id>[A-Z0-9]+)/delete\.(?P<format>[a-z]+)$', views.delete_acrelation_for_authority, name='delete_acrelation_for_authority_format'),

    url(r'^(?i)authority/$', views.authorities, name='authority_list'),

    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/attribute/$', views.attribute_for_citation, name='create_attribute_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/$', views.attribute_for_citation, name='update_attribute_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/delete/$', views.delete_attribute_for_citation, name='delete_attribute_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/delete\.(?P<format>[a-z]+)$', views.delete_attribute_for_citation, name='delete_attribute_for_citation_format'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/attribute/$', views.attribute_for_authority, name='create_attribute_for_authority'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/$', views.attribute_for_authority, name='update_attribute_for_authority'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/delete/$', views.delete_attribute_for_authority, name='delete_attribute_for_authority'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/delete\.(?P<format>[a-z]+)$', views.delete_attribute_for_authority, name='delete_attribute_for_authority_format'),

    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/linkeddata/(?P<linkeddata_id>[A-Z0-9]+)/delete/$', views.delete_linkeddata_for_citation, name='delete_linkeddata_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/linkeddata/(?P<linkeddata_id>[A-Z0-9]+)/delete\.(?P<format>[a-z]+)$', views.delete_linkeddata_for_citation, name='delete_linkeddata_for_citation_format'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/linkeddata/$', views.linkeddata_for_citation, name='create_linkeddata_for_citation'),
    url(r'^(?i)citation/(?P<citation_id>[A-Z0-9]+)/linkeddata/(?P<linkeddata_id>[A-Z0-9]+)/$', views.linkeddata_for_citation, name='update_linkeddata_for_citation'),

    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/linkeddata/(?P<linkeddata_id>[A-Z0-9]+)/delete/$', views.delete_linkeddata_for_authority, name='delete_linkeddata_for_authority'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/linkeddata/(?P<linkeddata_id>[A-Z0-9]+)/delete\.(?P<format>[a-z]+)$', views.delete_linkeddata_for_authority, name='delete_linkeddata_for_authority_format'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/linkeddata/$', views.linkeddata_for_authority, name='create_linkeddata_for_authority'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/linkeddata/(?P<linkeddata_id>[A-Z0-9]+)/$', views.linkeddata_for_authority, name='update_linkeddata_for_authority'),

    url(r'^(?i)acrelation/quickcreate/$', views.quick_create_acrelation, name='quick_create_acrelation'),

    url(r'^(?i)users/$', views.users, name='user_list'),
    url(r'^(?i)users/(?P<user_id>[0-9]+)$', views.user, name='user'),
    url(r'^(?i)users/role/remove/(?P<user_id>[0-9]+)/(?P<role_id>[0-9]+)$', views.remove_role, name='remove_role'),
    url(r'^(?i)users/addrole/(?P<user_edit_id>[0-9]+)/$', views.add_role_to_user, name='add_role_to_user'),
    url(r'^(?i)qdsearch/authority/$', views.quick_and_dirty_authority_search, name='quick_and_dirty_authority_search'),
    url(r'^(?i)qdsearch/citation/$', views.quick_and_dirty_citation_search, name='quick_and_dirty_citation_search'),
    url(r'^(?i)qdsearch/language/$', views.quick_and_dirty_language_search, name='quick_and_dirty_language_search'),
    url(r'^(?i)authority/(?P<authority_id>[A-Z0-9]+)/$', views.authority, name='curate_authority'),

    url(r'^(?i)users/role/$', views.add_role, name='create_role'),
    url(r'^(?i)users/roles/$', views.roles, name='roles'),
    url(r'^(?i)users/role/delete/(?P<role_id>[0-9]+)/$', views.delete_role, name='delete_role'),
    url(r'^(?i)users/role/(?P<role_id>[0-9]+)/$', views.role, name='role'),
    url(r'^(?i)users/rule/dataset/(?P<role_id>[0-9]+)/$', views.add_dataset_rule, name='create_rule_dataset'),
    url(r'^(?i)users/rule/crud/(?P<role_id>[0-9]+)/$', views.add_crud_rule, name='create_rule_crud'),
    url(r'^(?i)users/rule/field/(?P<role_id>[0-9]+)/(?P<object_type>((authority)|(citation))?)/$', views.add_field_rule, name='create_rule_citation_field'),
    url(r'^(?i)users/rule/user_module/(?P<role_id>[0-9]+)/$', views.add_user_module_rule, name='create_user_module_rule'),
    url(r'^(?i)users/rule/zotero/(?P<role_id>[0-9]+)/$', views.add_zotero_rule, name='add_zotero_rule'),
    url(r'^(?i)users/rule/remove/(?P<role_id>[0-9]+)/(?P<rule_id>[0-9]+)/$', views.remove_rule, name='remove_rule'),
    url(r'^(?i)users/role/staff/(?P<user_id>[0-9]+)$', views.change_is_staff, name='change_is_staff'),
    url(r'^(?i)users/role/superuser/(?P<user_id>[0-9]+)$', views.change_is_superuser, name='change_is_superuser'),
]
