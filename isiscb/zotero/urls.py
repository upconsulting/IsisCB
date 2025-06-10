from __future__ import unicode_literals
from django.conf.urls import include
from django.urls import re_path

from zotero.views import *

urlpatterns = [
    re_path(r'suggest/citation/(?P<citation_id>[0-9]+)/$', suggest_citation_json, name='suggest_citation'),
    re_path(r'suggest/authority/(?P<authority_id>[0-9]+)/$', suggest_authority_json, name='suggest_authority'),
    re_path(r'suggest/acrelation/(?P<acrelation_id>[0-9]+)/$', suggest_acrelation_json, name='suggest_acrelation'),
    re_path(r'suggest/acrelation/(?P<acrelation_id>[A-Z]+[0-9]+)/$', suggest_production_acrelation_json, name='suggest_production_acrelation'),

    re_path(r'data/accession/(?P<accession_id>[0-9]+)/$', data_importaccession, name='data_importaccession'),
    re_path(r'data/citation/(?P<draftcitation_id>[0-9]+)/$', data_draftcitation, name='data_draftcitation'),
    re_path(r'data/authority/(?P<draftauthority_id>[0-9]+)/$', data_draftauthority, name='data_draftauthority'),
    re_path(r'data/authority/(?P<draftauthority_id>[0-9]+)/edit/$', change_draftauthority, name='change_draftauthority'),

    re_path(r'accession/$', accessions, name='accessions'),
    re_path(r'accession/create/$', create_accession, name='create_accession'),
    re_path(r'accession/(?P<accession_id>[0-9]+)/$', retrieve_accession, name='retrieve_accession'),
    re_path(r'accession/(?P<accession_id>[0-9]+)/ingest/$', ingest_accession, name='ingest_accession'),
    re_path(r'accession/(?P<accession_id>[0-9]+)/matches/(?P<draftcitation_id>[0-9]+)$', possible_matching_citations, name='possible_matching_citations'),
    re_path(r'accession/(?P<accession_id>[0-9]+)/drafts/authority/(?P<draftauthority_id>[0-9]+)$', draft_authority, name='draft_authority'),

    re_path(r'authority/resolve/$', resolve_authority, name='resolve_authority'),
    re_path(r'authority/create/$', create_authority_for_draft, name='create_authority_for_draft'),
    re_path(r'authority/skip/$', skip_authority_for_draft, name='skip_authority_for_draft'),
    re_path(r'authority/similar/$', similar_authorities, name='similar_authorities'),

    re_path(r'citation/remove/$', remove_draftcitation, name='remove-draftcitation'),


]
