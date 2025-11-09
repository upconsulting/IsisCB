from django.db.models.functions import TruncYear
from django.db.models import Count

from isisdata.models import *

import logging, datetime
from haystack.query import SearchQuerySet

logger = logging.getLogger(__name__)

def generate_theses_by_school_context(top, chart_type, select_schools):
    
    if top == "CU":
        school_ids = select_schools.values_list('id', flat=True)
        schools = select_schools
    else:
        all_schools = Authority.objects.filter(
            public=True, 
            type_controlled=Authority.INSTITUTION, 
            acrelation__type_controlled=ACRelation.SCHOOL)
    
        # all schools ordered by how many theses there are for each
        all_schools = all_schools.annotate(num_theses=Count('acrelation', filter=Q(acrelation__citation__type_controlled=Citation.THESIS))).order_by('-num_theses')
        
        schools = all_schools[:top]
        school_ids = schools.values_list('id', flat=True)

    
    school_names = list(schools.values_list('name', flat=True))
    years = list(range(datetime.datetime(1970,1,1).year, datetime.datetime.today().year))
   
    # we don't need to check if authority is public since that will have taken care above when querying
    # for authorities
    thesis_school_acrs = ACRelation.objects.filter(
        public=True, 
        citation__public=True, 
        citation__type_controlled=Citation.THESIS, 
        citation__publication_date__year__in=years,
        authority__id__in=[school_ids])

                                                      
    if chart_type == "HG":
        values = get_data_for_heatgrid(school_ids, years, thesis_school_acrs)
        data = {
            'values': values,
            'names': school_names,
            'years': years,
        }
    elif chart_type == "NA" or chart_type == "ST" or chart_type == "AR":
        data = get_data_for_stacked_area(thesis_school_acrs, years, school_names)
    
    return {
        'data': data if data else [],
    }


def get_data_for_heatgrid(authority_ids, years, acrs):
    """
    this function takes a queryset of ACRs of theses 
    and converts them into a list of lists of the following form 
    (as desired by out-of-the-box D3 heatgrid graph (https://observablehq.com/@d3/the-impact-of-vaccines)):

    [
      [<thesis-count-for-school1-year1>, <thesis-count-for-school1-year-2>, etc.],
      [<thesis-count-for-school2-year1>, <thesis-count-for-school2-year-2>, etc.],
    ]

    py:function:: get_data_for_heatgrid(authority_ids, years, acrs)

    :param list authority_ids: a list of school ids
    :param list years: range of years which will serve as the domain of the graph
    :param queryset acrs: a queryset containing the ACRelations of each thesis for each of the schools
    :return: formatted data necessary for populating D3.js heatgrid graphs
    :rtype: list of lists
    """
    citations_count_per_year = []
    years_counts_template = [0] * len(years)

    for authority in authority_ids:
        citations_per_year_for_authority = years_counts_template.copy()
        authority_acrs = acrs.filter(authority__id=authority)

        for acr in authority_acrs:
            citations_per_year_for_authority[years.index(acr.citation.publication_date.year)] += 1

        citations_count_per_year.append(citations_per_year_for_authority)

    return citations_count_per_year

def get_data_for_stacked_area(acrs, years, schools):
    """
    this function takes a queryset of ACRs of theses 
    and converts them into a list of objects of the following form 
    (as desired by out-of-the-box D3 stacked area graphs):

    {
      "date": <date YYYY-MM-DD>,
      "school": <str name-of-school>,
      "theses": <int number-of-theses>
    }

    py:function:: get_data_for_stacked_area(acrs, years, schools)

    :param date date: a year
    :param str school: name of school that hosts theses
    :param int theses: the number of theses produced at each school in each year
    :return: formatted data necessary for populating D3.js area-type graphs
    :rtype: list of dicts
    """

    schools_years = { school : years.copy() for school in schools }
    
    values = []
    theses_per_school_per_year = acrs.values("authority__id")\
        .annotate(year=TruncYear('citation__publication_date'))\
        .values('year', 'authority__id')\
        .annotate(num_theses=Count('citation__id'))\
        .values('year', 'authority__name', 'num_theses')\
        .order_by('authority__name', 'year')
   
    for acr in theses_per_school_per_year:
        values.append({
            "date": acr['year'],
            "school": acr['authority__name'],
            "theses": acr['num_theses']
        })

        # creating a list of all the years with no data for each school
        if int(acr['year'].year) in schools_years[acr['authority__name']]:
            schools_years[acr['authority__name']].remove(int(acr['year'].year))
    
    # adding a new record to the data for all empty rows
    for school in schools_years: 
        for year in schools_years[school]:
            values.append({
                "date": datetime.date(year, 1, 1),
                "school": school,
                "theses": 0
            })
    
    # sort list of thesis year-school thesis counts by year and then school
    values = sorted(values, key=lambda k: (k['date'], k['school'].lower()))
    
    return values

def clean_dates(date_facet):
    new_date_facet = []
    for date in date_facet:
        logger.error(date_facet)
        date_pattern = re.compile("^[0-9]{4}$")
        if re.search(date_pattern, date[0]) and int(date[0]) >= 1965:
            new_date_facet.append(date)
    return new_date_facet

def get_ngram_data(authority_ids):
    sqs_all = SearchQuerySet().models(Citation).auto_query('*').facet('publication_date')
    all_facet_results = sqs_all.all().exclude(public="false")
    all_pub_date_facet = all_facet_results.facet_counts()['fields']['publication_date'] if 'fields' in all_facet_results.facet_counts() else []
    all_pub_date_facet = clean_dates(all_pub_date_facet)
    all_dates_map = {}
    citations = 0
    for facet in all_pub_date_facet:
        all_dates_map[facet[0]] = facet[1]
        citations = citations + facet[1]

    sqs = SearchQuerySet().models(Citation).facet('publication_date', size=200)

    facet_results = sqs.all().exclude(public="false").filter_or(author_ids__in=authority_ids).filter_or(contributor_ids__in=authority_ids) \
            .filter_or(editor_ids__in=authority_ids).filter_or(subject_ids__in=authority_ids).filter_or(institution_ids__in=authority_ids) \
            .filter_or(category_ids__in=authority_ids).filter_or(advisor_ids__in=authority_ids).filter_or(translator_ids__in=authority_ids) \
            .filter_or(publisher_ids__in=authority_ids).filter_or(school_ids__in=authority_ids).filter_or(meeting_ids__in=authority_ids) \
            .filter_or(periodical_ids__in=authority_ids).filter_or(book_series_ids__in=authority_ids).filter_or(time_period_ids__in=authority_ids) \
            .filter_or(geographic_ids__in=authority_ids).filter_or(about_person_ids__in=authority_ids).filter_or(other_person_ids__in=authority_ids)

    pub_date_facet = facet_results.facet_counts()['fields']['publication_date'] if 'fields' in facet_results.facet_counts() else []

    pub_date_facet = clean_dates(pub_date_facet)

    ngrams = []
    all_years = []
    all_ngrams = []

    for facet in pub_date_facet:
        all_years.append(int(facet[0]))
        date_facet = {}
        date_facet['year'] = facet[0]
        ngram = 100 * facet[1]/all_dates_map[facet[0]] if facet[0] in all_dates_map else 0
        ngram = round(ngram, 4)
        all_ngrams.append(ngram)
        date_facet['ngram'] = ngram
        ngrams.append(date_facet)

    ngrams = sorted(ngrams, key = lambda ngram: int(ngram['year']))

    return ngrams, max(all_years), min(all_years), max(all_ngrams)

def generate_genealogy_link(source, target, thesis, link_type):
    next_year = datetime.datetime.today().year + 1

    def generate_link_value():
        if link_type == "alma_mater":
            return next_year - thesis.publication_date.year if thesis.publication_date.year else 1
        else:
            return 15
        
    thesis_title = thesis.title if thesis.title else None
    thesis_year = thesis.publication_date.year if thesis.publication_date.year else None
    thesis_id = thesis.id

    link = {}
    link['source'] = source.id
    link['target'] = target.id
    link['value'] = generate_link_value()
    link['type'] = link_type
    link['thesis_title'] = thesis_title
    link['thesis_year'] = thesis_year
    link['thesis_id'] = thesis_id

    return link

def generate_genealogy_node(authority, associated_theses, subjects):
    theses_hosted_by_school = None
    theses_advised = None
    thesis_earliest = 0
    thesis_latest = 0
    employers = set()
    alma_mater = ''
    thesis_title = ''
    thesis_year = None
    theses_advised_count = 0
    node_associations = associated_theses.count()

    if authority.type_controlled == Authority.PERSON:
        thesis_written = associated_theses.filter(citation__public=True, authority__public=True, authority__id=authority.id, type_controlled=ACRelation.AUTHOR).values_list('citation__id', flat=True)
        alma_mater_acr = ACRelation.objects.filter(public=True, citation__id__in=thesis_written, type_controlled=ACRelation.SCHOOL).first()
        if alma_mater_acr:
            alma_mater = alma_mater_acr.authority.name
            thesis_title = alma_mater_acr.citation.title
            thesis_year = alma_mater_acr.citation.publication_date.year
        theses_advised = associated_theses.filter(type_controlled=ACRelation.ADVISOR)
        thesis_earliest = theses_advised.first().citation.publication_date.year if theses_advised and theses_advised.first().citation.publication_date else 0
        thesis_latest = theses_advised.last().citation.publication_date.year if theses_advised and theses_advised.last().citation.publication_date else 0
        theses_advised_ids = theses_advised.values_list('id', flat=True) if theses_advised else []
        theses_advised_count = theses_advised.count()
        theses_advised_schools = ACRelation.objects.filter(public=True, type_controlled=ACRelation.SCHOOL, citation__in=theses_advised_ids) 
        for school in theses_advised_schools:
            employers.add(school.authority.name)
    elif authority.type_controlled == Authority.INSTITUTION:
        theses_hosted_by_school = associated_theses.count()
        thesis_earliest = associated_theses.first().citation.publication_date.year
        thesis_latest = associated_theses.last().citation.publication_date.year

    node = {}
    node['id'] = authority.id
    node['name'] = authority.name
    node['type'] = authority.type_controlled
    node['selected'] = True if authority.id in subjects else False
    node['theses_hosted_by_school'] = theses_hosted_by_school
    node['theses_advised'] = theses_advised_count
    node['employers'] = list(employers)
    node['alma_mater'] = alma_mater
    node['thesis_title'] = thesis_title
    node['thesis_year'] = thesis_year
    node['thesis_earliest'] = thesis_earliest
    node['thesis_latest'] = thesis_latest
    node['num_associations'] = node_associations

    return node