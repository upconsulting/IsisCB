from django.conf.urls import url, include

from zotero.views import *

urlpatterns = [
    url(r'suggest/citation/(?P<citation_id>[0-9]+)/$', suggest_citation_json, name='suggest_citation'),
    url(r'suggest/authority/(?P<authority_id>[0-9]+)/$', suggest_authority_json, name='suggest_authority'),
    url(r'suggest/acrelation/(?P<acrelation_id>[0-9]+)/$', suggest_acrelation_json, name='suggest_acrelation'),
    url(r'suggest/acrelation/(?P<acrelation_id>[A-Z]+[0-9]+)/$', suggest_production_acrelation_json, name='suggest_production_acrelation'),

    url(r'data/accession/(?P<accession_id>[0-9]+)/$', data_importaccession, name='data_importaccession'),
    url(r'data/citation/(?P<draftcitation_id>[0-9]+)/$', data_draftcitation, name='data_draftcitation'),
    url(r'data/authority/(?P<draftauthority_id>[0-9]+)/$', data_draftauthority, name='data_draftauthority'),
    url(r'data/authority/(?P<draftauthority_id>[0-9]+)/edit/$', change_draftauthority, name='change_draftauthority'),

    url(r'accession/$', accessions, name='accessions'),
    url(r'accession/create/$', create_accession, name='create_accession'),
    url(r'accession/(?P<accession_id>[0-9]+)/$', retrieve_accession, name='retrieve_accession'),
    url(r'accession/(?P<accession_id>[0-9]+)/ingest/$', ingest_accession, name='ingest_accession'),

    url(r'authority/resolve/$', resolve_authority, name='resolve_authority'),
    url(r'authority/create/$', create_authority_for_draft, name='create_authority_for_draft'),
    url(r'authority/skip/$', skip_authority_for_draft, name='skip_authority_for_draft'),
    url(r'authority/similar/$', similar_authorities, name='similar_authorities'),

    url(r'citation/remove/$', remove_draftcitation, name='remove-draftcitation'),


]
