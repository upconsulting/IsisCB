from isisdata.models import *
from isisdata.helpers import external_services

from haystack.query import EmptySearchQuerySet, SearchQuerySet
from django import template
from django.core.paginator import Paginator

import requests

register = template.Library()


class RelatedCitationsSuperclass(template.Node):
    """
    Superclass for all related citations classes to e.g. print counts of related citations.
    """

    def __init__(self, authority_id, tenant_id, include_all_tenants):
        self.authority_id = template.Variable(authority_id)
        self.tenant_id = template.Variable(tenant_id)
        self.include_all_tenants = template.Variable(include_all_tenants)
        self.sqs = self._get_sqs()

    def _get_sqs(self):
        sqs = SearchQuerySet().models(Citation).facet('all_contributor_ids', size=100). \
                    facet('subject_ids', size=100).facet('institution_ids', size=100). \
                    facet('geographic_ids', size=1000).facet('time_period_ids', size=100).\
                    facet('category_ids', size=100).facet('other_person_ids', size=100).\
                    facet('publisher_ids', size=100).facet('periodical_ids', size=100).\
                    facet('concepts_by_subject_ids', size=100).facet('people_by_subject_ids', size=100).\
                    facet('institutions_by_subject_ids', size=100).facet('dataset_typed_names', size=100).\
                    facet('events_timeperiods_ids', size=100).facet('geocodes', size=1000)
    
        return sqs.all()
    
    def _get_related_citations(self, sqs, authority_id):
        related_citations = sqs.filter_or(author_ids=authority_id).filter_or(contributor_ids=authority_id) \
            .filter_or(editor_ids=authority_id).filter_or(subject_ids=authority_id).filter_or(institution_ids=authority_id) \
            .filter_or(category_ids=authority_id).filter_or(advisor_ids=authority_id).filter_or(translator_ids=authority_id) \
            .filter_or(publisher_ids=authority_id).filter_or(school_ids=authority_id).filter_or(meeting_ids=authority_id) \
            .filter_or(periodical_ids=authority_id).filter_or(book_series_ids=authority_id).filter_or(time_period_ids=authority_id) \
            .filter_or(geographic_ids=authority_id).filter_or(about_person_ids=authority_id).filter_or(other_person_ids=authority_id)
        related_citations = related_citations.all().exclude(public="false")
        
        return related_citations

    def _filter_by_tenant(self, sqs, tenant_id, include_all_tenants):
            """ Method that filters records by tenant if there are any and then returns the count"""
            if tenant_id and not include_all_tenants:
                tenant = Tenant.objects.filter(identifier=tenant_id).first()
                sqs = sqs.filter(owning_tenant=tenant.pk)
            return sqs
    
    def _get_filtered_related_citations(self, sqs, authority_id, tenant_id, include_all_tenants):
        """
        Get related citations
        """
        return self._filter_by_tenant(self._get_related_citations(sqs, authority_id).order_by('-publication_date_for_sort'), tenant_id, include_all_tenants)

    def _get_authors_contributors_count(self, sqs, authority_id, tenant_id, include_all_tenants):
        """
        Count citations with this authority as contributor
        """
        author_contributor_sqs = sqs.all().exclude(public="false").filter_or(author_ids=authority_id).filter_or(contributor_ids=authority_id) \
                .filter_or(editor_ids=authority_id).filter_or(advisor_ids=authority_id).filter_or(translator_ids=authority_id)
        return self._filter_by_tenant(author_contributor_sqs, tenant_id, include_all_tenants).count()
    
    def _get_publisher(self, sqs, authority_id, tenant_id, include_all_tenants):
        """
        Count citations with this authority as publisher
        """
        publisher_sqs = sqs.all().exclude(public="false").filter_or(publisher_ids=authority_id)
        return self._filter_by_tenant(publisher_sqs, tenant_id, include_all_tenants).count()

class RelatedCitationsCount(RelatedCitationsSuperclass):
    
    def __init__(self, authority_id, tenant_id, include_all_tenants):
        super(RelatedCitationsCount, self).__init__(authority_id, tenant_id, include_all_tenants)

    def render(self, context):
        authority_id = self.authority_id.resolve(context)
        tenant_id = self.tenant_id.resolve(context)
        include_all_tenants = self.include_all_tenants.resolve(context)
        
        related_citations = self._get_filtered_related_citations(self.sqs, authority_id, tenant_id, include_all_tenants)
        context['related_citations'] = related_citations
        context['related_citations_count'] =  related_citations.count()
        
        self._add_subject_categories(context, self.sqs, authority_id, tenant_id, include_all_tenants)
        context['author_contributor_count'] = self._get_authors_contributors_count(self.sqs, authority_id, tenant_id, include_all_tenants)
        context['publisher_count'] = self._get_publisher(self.sqs, authority_id, tenant_id, include_all_tenants)

        return ""

    def _add_subject_categories(self, context, sqs, authority_id, tenant_id, include_all_tenants):
        """
        Count citations with this authority as subject or as category.
        """
        subject_category_sqs = self.sqs.all().exclude(public="false").filter_or(subject_ids=authority_id).filter_or(category_ids=authority_id)
        context['subject_category_count'] = self._filter_by_tenant(subject_category_sqs, tenant_id, include_all_tenants).count()     
    
    
    def _add_geographic_factets(self, context, sqs, authority_id, tenant_id, include_all_tenants):
        related_citations = context['related_citations']
        related_geographics_facets = related_citations.facet_counts()['fields']['geographic_ids'] if 'fields' in related_citations.facet_counts() else []
        related_geographics_facets = self._remove_self_from_facets(related_geographics_facets, authority_id)
        context['related_geographics_facets'] = related_geographics_facets

    def _remove_self_from_facets(self, facet, authority_id):
        return [x for x in facet if x[0].upper() != authority_id.upper()]

class WikipediaInfo(RelatedCitationsSuperclass):

    def __init__(self, authority_id, tenant_id, include_all_tenants):
        super(WikipediaInfo, self).__init__(authority_id, tenant_id, include_all_tenants)

    def render(self, context):
        authority_id = self.authority_id.resolve(context)
        tenant_id = self.tenant_id.resolve(context)
        include_all_tenants = self.include_all_tenants.resolve(context)

        authority = Authority.objects.get(id=authority_id)
        authors_contributors_count = self._get_authors_contributors_count(self.sqs, authority_id, tenant_id, include_all_tenants)
        publisher_count = self._get_publisher(self.sqs, authority_id, tenant_id, include_all_tenants)
        related_citations = self._get_filtered_related_citations(self.sqs, authority_id, tenant_id, include_all_tenants)
        
        display_type = self._get_display_type(authority, authors_contributors_count, publisher_count, related_citations.count())
        context["display_type"] = display_type

        wikiImage, wikiIntro, wikiCredit = external_services.get_wikipedia_image_synopsis(authority, authors_contributors_count, related_citations.count())
        context["wikiImage"] = wikiImage
        context['wikiIntro'] = wikiIntro
        context['wikiCredit'] = wikiCredit
          
        return ""

    def _get_display_type(self, authority, author_contributor_count, publisher_count, related_citations_count):
        if authority.type_controlled == authority.PERSON and author_contributor_count != 0 and related_citations_count !=0 and author_contributor_count/related_citations_count > .9:
            return 'Author'
        elif authority.type_controlled == authority.INSTITUTION and publisher_count != 0 and related_citations_count !=0 and publisher_count/related_citations_count > .9:
            return 'Publisher'
        else:
            return authority.get_type_controlled_display

class RelatedCitationsList(RelatedCitationsSuperclass):

    def __init__(self, authority_id, tenant_id, include_all_tenants, page_citation):
        super(RelatedCitationsList, self).__init__(authority_id, tenant_id, include_all_tenants)
        self.page_citation = template.Variable(page_citation)

    def render(self, context):
        authority_id = self.authority_id.resolve(context)
        tenant_id = self.tenant_id.resolve(context)
        include_all_tenants = self.include_all_tenants.resolve(context)
        page_citation = self.page_citation.resolve(context) if 'page_citation' in context else 1

        related_citations = self._get_related_citations(self.sqs, authority_id)
        related_citations = self._filter_by_tenant(related_citations.order_by('-publication_date_for_sort'), tenant_id, include_all_tenants)
    
        page_number = page_citation if page_citation else 1
        paginator = Paginator(related_citations, 20)
        context['page_results'] = paginator.get_page(page_number)
        return ""

class AuthorityFacets(RelatedCitationsSuperclass):
    
    def __init__(self, authority_id, tenant_id, include_all_tenants):
        super(AuthorityFacets, self).__init__(authority_id, tenant_id, include_all_tenants)
        
    def render(self, context):
        authority_id = self.authority_id.resolve(context)
        tenant_id = self.tenant_id.resolve(context)
        include_all_tenants = self.include_all_tenants.resolve(context)

        search_results = self._get_filtered_related_citations(self.sqs, authority_id, tenant_id, include_all_tenants)
        subject_ids_facet = search_results.facet_counts()['fields']['subject_ids'] if 'fields' in search_results.facet_counts() else []
        related_contributors_facet = search_results.facet_counts()['fields']['all_contributor_ids'] if 'fields' in search_results.facet_counts() else []
        related_institutions_facet = search_results.facet_counts()['fields']['institution_ids'] if 'fields' in search_results.facet_counts() else []
        related_geographics_facet = search_results.facet_counts()['fields']['geographic_ids'] if 'fields' in search_results.facet_counts() else []
        related_timeperiod_facet = search_results.facet_counts()['fields']['events_timeperiods_ids'] if 'fields' in search_results.facet_counts() else []
        related_categories_facet = search_results.facet_counts()['fields']['category_ids'] if 'fields' in search_results.facet_counts() else []
        related_other_person_facet = search_results.facet_counts()['fields']['other_person_ids'] if 'fields' in search_results.facet_counts() else []
        related_publisher_facet = search_results.facet_counts()['fields']['publisher_ids'] if 'fields' in search_results.facet_counts() else []
        related_journal_facet = search_results.facet_counts()['fields']['periodical_ids'] if 'fields' in search_results.facet_counts() else []
        related_subject_concepts_facet = search_results.facet_counts()['fields']['concepts_by_subject_ids'] if 'fields' in search_results.facet_counts() else []
        related_subject_people_facet = search_results.facet_counts()['fields']['people_by_subject_ids'] if 'fields' in search_results.facet_counts() else []
        related_subject_institutions_facet = search_results.facet_counts()['fields']['institutions_by_subject_ids'] if 'fields' in search_results.facet_counts() else []
        related_dataset_facet = search_results.facet_counts()['fields']['dataset_typed_names'] if 'fields' in search_results.facet_counts() else []

        # remove current authority from facet results
        subject_ids_facet = self._remove_self_from_facets(subject_ids_facet, authority_id)
        related_contributors_facet =self._remove_self_from_facets(related_contributors_facet, authority_id)
        related_institutions_facet = self._remove_self_from_facets(related_institutions_facet, authority_id)
        related_geographics_facet = self._remove_self_from_facets(related_geographics_facet, authority_id)
        related_timeperiod_facet = self._remove_self_from_facets(related_timeperiod_facet, authority_id)
        related_categories_facet = self._remove_self_from_facets(related_categories_facet, authority_id)
        related_other_person_facet = self._remove_self_from_facets(related_other_person_facet, authority_id)
        related_publisher_facet = self._remove_self_from_facets(related_publisher_facet, authority_id)
        related_journal_facet = self._remove_self_from_facets(related_journal_facet, authority_id)
        related_subject_concepts_facet = self._remove_self_from_facets(related_subject_concepts_facet, authority_id)
        related_subject_people_facet = self._remove_self_from_facets(related_subject_people_facet, authority_id)
        related_subject_institutions_facet = self._remove_self_from_facets(related_subject_institutions_facet, authority_id)
        related_dataset_facet = self._remove_self_from_facets(related_dataset_facet, authority_id)

        context['subject_ids_facet'] = subject_ids_facet
        context['related_contributors_facet'] = related_contributors_facet
        context['related_institutions_facet'] = related_institutions_facet
        context['related_geographics_facet'] = related_geographics_facet
        context['related_timeperiod_facet'] = related_timeperiod_facet
        context['related_categories_facet'] = related_categories_facet
        context['related_other_person_facet'] = related_other_person_facet
        context['related_publisher_facet'] = related_publisher_facet
        context['related_journal_facet'] = related_journal_facet
        context['related_subject_concepts_facet'] = related_subject_concepts_facet
        context['related_subject_people_facet'] = related_subject_people_facet
        context['related_subject_institutions_facet'] = related_subject_institutions_facet
        context['related_dataset_facet'] = related_dataset_facet
        
        return ""

    def _remove_self_from_facets(self, facet, authority_id):
        return [x for x in facet if x[0].upper() != authority_id.upper()]

@register.tag(name="related_citation_count")
def do_related_citation_count(parser, token):
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, authority_id, tenant_id, include_all_tenants = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            "%r tag requires a 3 arguments" % token.contents.split()[0]
        )
    return RelatedCitationsCount(authority_id, tenant_id, include_all_tenants)

@register.tag(name="wikipedia_info")
def do_wikipedia_info(parser, token):
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, authority_id, tenant_id, include_all_tenants = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            "%r tag requires a 3 arguments" % token.contents.split()[0]
        )
    return WikipediaInfo(authority_id, tenant_id, include_all_tenants)

@register.tag(name="related_citations_list")
def do_related_citations_list(parser, token):
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, authority_id, tenant_id, include_all_tenants, page_nr = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            "%r tag requires a 4 arguments" % token.contents.split()[0]
        )
    return RelatedCitationsList(authority_id, tenant_id, include_all_tenants, page_nr)

@register.tag(name="authority_facets")
def do_authority_facets(parser, token):
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, authority_id, tenant_id, include_all_tenants = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            "%r tag requires a 3 arguments" % token.contents.split()[0]
        )
    return AuthorityFacets(authority_id, tenant_id, include_all_tenants)