from __future__ import unicode_literals
from django import template
from isisdata.models import *
import isisdata.google as google

import pytz, random, requests
from urllib.request import urlopen
from haystack.query import EmptySearchQuerySet, SearchQuerySet
from django.shortcuts import get_object_or_404
from isisdata.helpers import external_services
from haystack.inputs import Raw, AutoQuery
import logging

register = template.Library()
logger = logging.getLogger(__name__)

@register.filter
def get_featured_citation(tenant_id):
    tenant = None
    if tenant_id:
        tenant = get_object_or_404(Tenant, identifier=tenant_id)
   
     # Get featured citation and authority
    now = datetime.datetime.now(pytz.timezone(settings.ADMIN_TIMEZONE))
    
    current_featured_authorities = FeaturedAuthority.objects.filter(start_date__lt=now, authority__owning_tenant=tenant).filter(end_date__gt=now)
    current_featured_authority_ids = [featured_authority.authority.id for featured_authority in current_featured_authorities]
    
    sqs = SearchQuerySet().models(Citation)
    sqs.query.set_limits(low=0, high=30)
    # featured_citations = sqs.all().exclude(public="false").filter(abstract = Raw("[* TO *]")).filter(title = Raw("[* TO *]")).query.get_results()
    featured_citations = sqs.all().exclude(public="false")
    if tenant:
        featured_citations = featured_citations.filter(subject_ids__in=current_featured_authority_ids, owning_tenant=tenant.id).filter(type__in=['Book', 'Article']).filter(abstract = Raw("[* TO *]")).filter(title = Raw("[* TO *]")).query.get_results()
    else:
        featured_citations = featured_citations.filter(subject_ids__in=current_featured_authority_ids).filter(type__in=['Book', 'Article']).filter(abstract = Raw("[* TO *]")).filter(title = Raw("[* TO *]")).query.get_results()

    if featured_citations:
        featured_citation = featured_citations[random.randint(0,len(featured_citations)-1)]
        featured_citation = Citation.objects.filter(pk=featured_citation.id).first()
    elif tenant and tenant.settings and tenant.settings.default_featured_citation:
        featured_citation = tenant.settings.default_featured_citation
    else:
        #set default featured citation in case no featured authorities have been selected
        featured_citation = Citation.objects.filter(pk=settings.FEATURED_CITATION_ID).first()

    return featured_citation

@register.filter
def get_featured_citation_image(featured_citation):
     return google.get_google_books_image(featured_citation, True)

@register.filter
def get_featured_citation_properties(featured_citation):
    return list(featured_citation.acrelation_set.exclude(type_controlled__in=[ACRelation.AUTHOR, ACRelation.EDITOR, ACRelation.CONTRIBUTOR, ACRelation.SUBJECT, ACRelation.CATEGORY]).filter(public=True))
    
@register.filter
def get_featured_citation_authors(featured_citation):
    return featured_citation.acrelation_set.filter(type_controlled__in=[ACRelation.AUTHOR, ACRelation.CONTRIBUTOR, ACRelation.EDITOR], citation__public=True, public=True)
     
@register.filter
def get_featured_authorities(tenant_id):
    tenant = None
    if tenant_id:
        tenant = get_object_or_404(Tenant, identifier=tenant_id)
   
    # Get featured citation and authority
    now = datetime.datetime.now(pytz.timezone(settings.ADMIN_TIMEZONE))

    current_featured_authorities = FeaturedAuthority.objects.filter(start_date__lt=now, authority__owning_tenant=tenant).filter(end_date__gt=now)
    current_featured_authority_ids = [featured_authority.authority.id for featured_authority in current_featured_authorities]
    featured_authorities = Authority.objects.filter(id__in=current_featured_authority_ids, owning_tenant=tenant).exclude(wikipediadata__intro='')
   
    if featured_authorities:
        featured_authority = featured_authorities[random.randint(0,len(featured_authorities)-1)]
    elif tenant and tenant.settings and tenant.settings.default_featured_authority:
        featured_authority = tenant.settings.default_featured_authority
    else:
        #set default featured authorities in case no featured authorities have been selected
        featured_authority = Authority.objects.filter(pk=settings.FEATURED_AUTHORITY_ID).first()

    return featured_authority

@register.filter
def get_wiki_data(featured_authority):
    #Get authority related citations and authors/contribs counts so they can be used to get wikipedia data
    sqs = SearchQuerySet().models(Citation)

    related_citations_count = sqs.all().exclude(public="false").filter_or(author_ids=featured_authority.id).filter_or(contributor_ids=featured_authority.id) \
            .filter_or(editor_ids=featured_authority.id).filter_or(subject_ids=featured_authority.id).filter_or(institution_ids=featured_authority.id) \
            .filter_or(category_ids=featured_authority.id).filter_or(advisor_ids=featured_authority.id).filter_or(translator_ids=featured_authority.id) \
            .filter_or(publisher_ids=featured_authority.id).filter_or(school_ids=featured_authority.id).filter_or(meeting_ids=featured_authority.id) \
            .filter_or(periodical_ids=featured_authority.id).filter_or(book_series_ids=featured_authority.id).filter_or(time_period_ids=featured_authority.id) \
            .filter_or(geographic_ids=featured_authority.id).filter_or(about_person_ids=featured_authority.id).filter_or(other_person_ids=featured_authority.id) \
            .count()

    author_contributor_count = sqs.all().exclude(public="false").filter_or(author_ids=featured_authority.id).filter_or(contributor_ids=featured_authority.id) \
            .filter_or(editor_ids=featured_authority.id).filter_or(advisor_ids=featured_authority.id).filter_or(translator_ids=featured_authority.id).count()

    # get wikipedia data
    wikiImage, wikiIntro, wikiCredit = external_services.get_wikipedia_image_synopsis(featured_authority, author_contributor_count, related_citations_count)
    return (wikiImage, wikiIntro, wikiCredit)


       