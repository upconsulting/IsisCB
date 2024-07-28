from isisdata.models import *
from haystack.query import EmptySearchQuerySet, SearchQuerySet
from django import template

import logging

register = template.Library()
logger = logging.getLogger(__name__)

@register.inclusion_tag("isisdata/citation_fragments/fragment_similar_citations.html", takes_context=True)
def get_similar_citations_and_facets(context, citation):
    return _get_data(context, citation)

@register.inclusion_tag("tenants/citation_fragments/fragment_similar_citations.html", takes_context=True)
def get_tenant_similar_citations_and_facets(context, citation):
    return _get_data(context, citation)

def _get_data(context, citation):
    tenant_id = context["tenant_id"]
    include_all_tenants = context["include_all_tenants"]
    tenant = Tenant.objects.filter(identifier=tenant_id).first() if tenant_id else None

    subjects = citation.acrelation_set.filter(Q(type_controlled__in=[ACRelation.SUBJECT], citation__public=True, public=True))
    if subjects:
        sqs = SearchQuerySet().models(Citation).facet('all_contributor_ids', size=100). \
                facet('subject_ids', size=100).facet('institution_ids', size=100). \
                facet('geographic_ids', size=1000).facet('time_period_ids', size=100).\
                facet('category_ids', size=100).facet('other_person_ids', size=100).\
                facet('publisher_ids', size=100).facet('periodical_ids', size=100).\
                facet('concepts_by_subject_ids', size=100).facet('people_by_subject_ids', size=100).\
                facet('institutions_by_subject_ids', size=100).facet('dataset_typed_names', size=100).\
                facet('events_timeperiods_ids', size=100).facet('geocodes', size=1000)
        sqs.query.set_limits(low=0, high=20)
        results = sqs.all().exclude(public="false")
        if tenant and not include_all_tenants:
            results = results.filter(tenant_ids=tenant.pk)

        subject_ids = [subject.authority.id for subject in context['subjects'] if subject.authority]
        similar_citations = results.filter(subject_ids__in=subject_ids).exclude(id=citation.id).query.get_results()
    elif citation.type_controlled not in ['RE']:
        mlt = SearchQuerySet().models(Citation).more_like_this(citation).facet('all_contributor_ids', size=100). \
                facet('subject_ids', size=100).facet('institution_ids', size=100). \
                facet('geographic_ids', size=1000).facet('time_period_ids', size=100).\
                facet('category_ids', size=100).facet('other_person_ids', size=100).\
                facet('publisher_ids', size=100).facet('periodical_ids', size=100).\
                facet('concepts_by_subject_ids', size=100).facet('people_by_subject_ids', size=100).\
                facet('institutions_by_subject_ids', size=100).facet('dataset_typed_names', size=100).\
                facet('events_timeperiods_ids', size=100).facet('geocodes', size=1000)
        mlt.query.set_limits(low=0, high=20)
        if tenant and not include_all_tenants:
            mlt = mlt.filter(tenant_ids=tenant_id)
        similar_citations = mlt.all().exclude(public="false").query.get_results()
    else:
        similar_citations = []

    if tenant and not include_all_tenants:
        similar_objects = _get_facets_from_citations([citation.id for citation in similar_citations], tenant_id=tenant.pk)
    else:
        similar_objects = _get_facets_from_citations([citation.id for citation in similar_citations])
        
    return {
        "similar_citations":similar_citations,
        'facets': similar_objects.facet_counts(),
        'tenant_id': tenant_id,
        'user': context['request'].user,
        }

def _get_facets_from_citations(citations, tenant_id=None):
    sqs = SearchQuerySet().models(Citation).facet('all_contributor_ids', size=100). \
                facet('subject_ids', size=100).facet('institution_ids', size=100). \
                facet('geographic_ids', size=1000).facet('time_period_ids', size=100).\
                facet('category_ids', size=100).facet('other_person_ids', size=100).\
                facet('publisher_ids', size=100).facet('periodical_ids', size=100).\
                facet('concepts_only_by_subject_ids', size=100).\
                facet('institutional_host_ids', size=100).\
                facet('about_person_ids', size=100).\
                facet('concepts_by_subject_ids', size=100).facet('people_by_subject_ids', size=100).\
                facet('institutions_by_subject_ids', size=100).facet('dataset_typed_names', size=100).\
                facet('events_timeperiods_ids', size=100).facet('geocodes', size=1000).\
                facet('publication_host_ids', size=100)
   
    # filter by tenant if tenant is identified
    if tenant_id:
        sqs = sqs.filter(tenant_ids=tenant_id)
    
    # filter by citation ids
    sqs = sqs.filter(id__in=citations).exclude(public="false")

    return sqs