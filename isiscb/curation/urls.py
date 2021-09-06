from __future__ import absolute_import
from __future__ import unicode_literals


from curation import views
from curation.bulk_views import bulk_change_csv_views
from curation.bulk_views import citation_views
from curation.authority_views import relation_views as authority_relation_views
from curation.authority_views import aarset_views as aarset_views
from curation.citation_views import tracking_views
import rules
from .rules import *
from django.urls import re_path

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

app_name = "curation"
urlpatterns = [
    re_path(r'^$', views.dashboard, name='index'),
    re_path(r'^dashboard/$', views.dashboard, name='dashboard'),
    re_path(r'^datasets/$', views.datasets, name='datasets'),
    re_path(r'^citation/$', views.citations, name='citation_list'),
    re_path(r'^bulk$', bulk_change_csv_views.bulk_changes, name='bulk_changes'),
    re_path(r'^bulk/csv$', bulk_change_csv_views.bulk_change_from_csv, name='general_bulk_change_from_csv'),
    re_path(r'^bulk/csv/status$', bulk_change_csv_views.bulk_csv_status, name="bulk-csv-status"),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/$', views.citation, name='curate_citation'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/$', views.authority, name='curate_authority'),

    re_path(r'^api/citation$', views.get_citation_by_id, name='api_citation'),

    re_path(r'^timelines$', bulk_change_csv_views.timeline_tasks, name='timeline_tasks'),
    re_path(r'^timelines/(?P<authority_id>[A-Z0-9]+)/delete$', bulk_change_csv_views.timeline_delete, name='delete_timeline'),

    re_path(r'^citation/add$', views.create_citation, name="create_citation"),
    re_path(r'^authority/add$', views.create_authority, name="create_authority"),

    re_path(r'^authority/export$', views.export_authorities, name="export-authorities"),
    re_path(r'^authority/export/status$', views.export_authorities_status, name="export-authorities-status"),

    re_path(r'^zotero/accessions/search$', views.search_zotero_accessions, name='search-zotero-accessions'),
    re_path(r'^zotero/linkeddata/type/search$', views.search_linked_data_type, name='search-linked-data-type'),

    re_path(r'^datasets/search$', views.search_datasets, name='search-datasets'),
    re_path(r'^users/search$', views.search_users, name='search-users'),

    re_path(r'^citation/collection$', views.collections, name='collections'),
    re_path(r'^citation/collection/search$', views.search_citation_collections, name='search-collections'),
    re_path(r'^citation/collection/create$', views.create_citation_collection, name='create-citation-collection'),
    re_path(r'^citation/collection/add$', views.add_citation_collection, name='add-citation-collection'),
    re_path(r'^citation/bulk$', views.bulk_action, name='citation-bulk-action'),
    re_path(r'^citation/bulk/status$', views.bulk_action_status, name='citation-bulk-action-status'),
    re_path(r'^citation/bulk/ccr/create$', citation_views.bulk_create_ccr, name='bulk-create-ccr'),
    re_path(r'^citation/export$', views.export_citations, name="export-citations"),
    re_path(r'^citation/export/status$', views.export_citations_status, name="export-citations-status"),
    re_path(r'^citation/select$', views.bulk_select_citation, name='citation-bulk-select'),

    re_path(r'^authority/collection$', views.authority_collections, name='authority-collections'),
    re_path(r'^authority/collection/add$', views.add_authority_collection, name='add-authority-collection'),
    re_path(r'^authority/collection/search$', views.search_authority_collections, name='search-authority-collections'),
    re_path(r'^authority/collection/create$', views.create_authority_collection, name='create-authority-collection'),
    re_path(r'^authority/bulk/csv$', bulk_change_csv_views.bulk_change_from_csv, name='bulk_change_from_csv'),
    re_path(r'^authority/select$', views.bulk_select_authority, name='authority-bulk-select'),

    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/tracking$', views.tracking_for_citation, name='tracking-citation'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/tracking/(?P<tracking_id>[A-Z0-9]+)$', tracking_views.delete_tracking_for_citation, name='delete-tracking-citation'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/tracking/proof-activate$', tracking_views.proof_and_set_active, name='proof-set-active'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/tracking$', views.tracking_for_authority, name='tracking-authority'),

    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/ccrelation/$', views.create_ccrelation_for_citation, name='create_ccrelation_for_citation'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/ccrelation/(?P<ccrelation_id>[A-Z0-9]+)/$', views.ccrelation_for_citation, name='ccrelation_for_citation'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/ccrelation/(?P<ccrelation_id>[A-Z0-9]+)/delete/$', views.delete_ccrelation_for_citation, name='delete_ccrelation_for_citation'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/ccrelation/(?P<ccrelation_id>[A-Z0-9]+)/delete\.(?P<format>[a-z]+)$', views.delete_ccrelation_for_citation, name='delete_ccrelation_for_citation_format'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/language/remove/$', views.delete_language_for_citation, name='delete_language_for_citation'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/language/add/$', views.add_language_for_citation, name='add_language_for_citation'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/type/change$', views.change_record_type, name='change_record_type'),

    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/acrelation/$', views.create_acrelation_for_citation, name='create_acrelation_for_citation'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/acrelation/(?P<acrelation_id>[A-Z0-9]+)/$', views.acrelation_for_citation, name='update_acrelation_for_citation'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/acrelation/(?P<acrelation_id>[A-Z0-9]+)/delete/$', views.delete_acrelation_for_citation, name='delete_acrelation_for_citation'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/acrelation/(?P<acrelation_id>[A-Z0-9]+)/delete\.(?P<format>[a-z]+)$', views.delete_acrelation_for_citation, name='delete_acrelation_for_citation_format'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/acrelation/$', authority_relation_views.create_acrelation_for_authority, name='create_acrelation_for_authority'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/aarelation/$', authority_relation_views.create_aarelation_for_authority, name='create_aarelation_for_authority'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/acrelation/(?P<acrelation_id>[A-Z0-9]+)/$', authority_relation_views.acrelation_for_authority, name='update_acrelation_for_authority'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/aarelation/(?P<aarelation_id>[A-Z0-9]+)/$', authority_relation_views.aarelation_for_authority, name='update_aarelation_for_authority'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/acrelation/(?P<acrelation_id>[A-Z0-9]+)/delete/$', views.delete_acrelation_for_authority, name='delete_acrelation_for_authority'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/aarelation/(?P<aarelation_id>[A-Z0-9]+)/delete/$', authority_relation_views.delete_aarelation_for_authority, name='delete_aarelation_for_authority'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/acrelation/(?P<acrelation_id>[A-Z0-9]+)/delete\.(?P<format>[a-z]+)$', views.delete_acrelation_for_authority, name='delete_acrelation_for_authority_format'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/aarelation/(?P<aarelation_id>[A-Z0-9]+)/delete\.(?P<format>[a-z]+)$', authority_relation_views.delete_aarelation_for_authority, name='delete_aarelation_for_authority_format'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/acrelations/$', views.authority_acrelations, name='authority_acrelations'),

    re_path(r'^authority/$', views.authorities, name='authority_list'),

    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/attribute/$', views.attribute_for_citation, name='create_attribute_for_citation'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/$', views.attribute_for_citation, name='update_attribute_for_citation'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/delete/$', views.delete_attribute_for_citation, name='delete_attribute_for_citation'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/delete\.(?P<format>[a-z]+)$', views.delete_attribute_for_citation, name='delete_attribute_for_citation_format'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/attribute/$', views.attribute_for_authority, name='create_attribute_for_authority'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/$', views.attribute_for_authority, name='update_attribute_for_authority'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/delete/$', views.delete_attribute_for_authority, name='delete_attribute_for_authority'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/attribute/(?P<attribute_id>[A-Z0-9]+)/delete\.(?P<format>[a-z]+)$', views.delete_attribute_for_authority, name='delete_attribute_for_authority_format'),

    re_path(r'^attributetype/(?P<attribute_type_id>[0-9]+)/helptext$', views.get_attribute_type_help_text, name='get_attribute_type_help_text'),

    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/linkeddata/(?P<linkeddata_id>[A-Z0-9]+)/delete/$', views.delete_linkeddata_for_citation, name='delete_linkeddata_for_citation'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/linkeddata/(?P<linkeddata_id>[A-Z0-9]+)/delete\.(?P<format>[a-z]+)$', views.delete_linkeddata_for_citation, name='delete_linkeddata_for_citation_format'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/linkeddata/$', views.linkeddata_for_citation, name='create_linkeddata_for_citation'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/linkeddata/(?P<linkeddata_id>[A-Z0-9]+)/$', views.linkeddata_for_citation, name='update_linkeddata_for_citation'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/linkeddata/duplicates$', views.citation_linkeddata_duplicates, name='citation_linkeddata_duplicates'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/linkeddata/duplicates/delete$', views.citation_delete_linkeddata_duplicates, name='citation_delete_linkeddata_duplicates'),

    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/subjects/$', views.subjects_and_categories, name='subjects_and_categories'),
    re_path(r'^citation/(?P<citation_id>[A-Z0-9]+)/suggestions/$', views.get_subject_suggestions, name='subjects_suggestions'),

    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/linkeddata/(?P<linkeddata_id>[A-Z0-9]+)/delete/$', views.delete_linkeddata_for_authority, name='delete_linkeddata_for_authority'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/linkeddata/(?P<linkeddata_id>[A-Z0-9]+)/delete\.(?P<format>[a-z]+)$', views.delete_linkeddata_for_authority, name='delete_linkeddata_for_authority_format'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/linkeddata/$', views.linkeddata_for_authority, name='create_linkeddata_for_authority'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/linkeddata/(?P<linkeddata_id>[A-Z0-9]+)/$', views.linkeddata_for_authority, name='update_linkeddata_for_authority'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/linkeddata/duplicates$', views.authority_linkeddata_duplicates, name='authority_linkeddata_duplicates'),
    re_path(r'^authority/(?P<authority_id>[A-Z0-9]+)/linkeddata/duplicates/delete$', views.authority_delete_linkeddata_duplicates, name='authority_delete_linkeddata_duplicates'),

    re_path(r'^acrelation/quickcreate/$', views.quick_create_acrelation, name='quick_create_acrelation'),

    re_path(r'^aarsets/$', aarset_views.aarsets, name='aarsets'),
    re_path(r'^aarsets/aarset/$', aarset_views.change_aarset, name='create_aarset'),
    re_path(r'^aarsets/aarset/(?P<aarset_id>[A-Z0-9]+)/edit$', aarset_views.change_aarset, name='edit_aarset'),
    re_path(r'^aarsets/aarset/(?P<aarset_id>[A-Z0-9]+)$', aarset_views.view_aarset, name='view_aarset'),
    re_path(r'^aarsets/aarset/(?P<aarset_id>[A-Z0-9]+)/delete$', aarset_views.delete_aarset, name='delete_aarset'),
    re_path(r'^aarsets/aarset/(?P<aarset_id>[A-Z0-9]+)/type$', aarset_views.change_aartype, name='create_aartype'),
    re_path(r'^aarsets/aarset/(?P<aarset_id>[A-Z0-9]+)/type/(?P<aartype_id>[A-Z0-9]+)$', aarset_views.change_aartype, name='edit_aartype'),

    re_path(r'^users/$', views.users, name='user_list'),
    re_path(r'^users/(?P<user_id>[0-9]+)$', views.user, name='user'),
    re_path(r'^users/role/remove/(?P<user_id>[0-9]+)/(?P<role_id>[0-9]+)$', views.remove_role, name='remove_role'),
    re_path(r'^users/addrole/(?P<user_edit_id>[0-9]+)/$', views.add_role_to_user, name='add_role_to_user'),
    re_path(r'^qdsearch/authority/$', views.quick_and_dirty_authority_search, name='quick_and_dirty_authority_search'),
    re_path(r'^qdsearch/citation/$', views.quick_and_dirty_citation_search, name='quick_and_dirty_citation_search'),
    re_path(r'^qdsearch/language/$', views.quick_and_dirty_language_search, name='quick_and_dirty_language_search'),

    re_path(r'^users/role/$', views.add_role, name='create_role'),
    re_path(r'^users/roles/$', views.roles, name='roles'),
    re_path(r'^users/role/delete/(?P<role_id>[0-9]+)/$', views.delete_role, name='delete_role'),
    re_path(r'^users/role/(?P<role_id>[0-9]+)/$', views.role, name='role'),
    re_path(r'^users/rule/dataset/(?P<role_id>[0-9]+)/$', views.add_dataset_rule, name='create_rule_dataset'),
    re_path(r'^users/rule/crud/(?P<role_id>[0-9]+)/$', views.add_crud_rule, name='create_rule_crud'),
    re_path(r'^users/rule/field/(?P<role_id>[0-9]+)/(?P<object_type>((authority)|(citation))?)/$', views.add_field_rule, name='create_rule_citation_field'),
    re_path(r'^users/rule/user_module/(?P<role_id>[0-9]+)/$', views.add_user_module_rule, name='create_user_module_rule'),
    re_path(r'^users/rule/zotero/(?P<role_id>[0-9]+)/$', views.add_zotero_rule, name='add_zotero_rule'),
    re_path(r'^users/rule/remove/(?P<role_id>[0-9]+)/(?P<rule_id>[0-9]+)/$', views.remove_rule, name='remove_rule'),
    re_path(r'^users/role/staff/(?P<user_id>[0-9]+)$', views.change_is_staff, name='change_is_staff'),
    re_path(r'^users/role/superuser/(?P<user_id>[0-9]+)$', views.change_is_superuser, name='change_is_superuser'),
]
