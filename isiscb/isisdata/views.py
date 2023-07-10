from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import object
from django import forms
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger, InvalidPage
from django.core.cache import caches
from django.core.cache.backends.base import InvalidCacheBackendError
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import connection
from django.db.models import Q, Prefetch, Count, Subquery, OuterRef, Case, When, IntegerField
from django.http import HttpResponse, HttpResponseForbidden, Http404, HttpResponseRedirect, JsonResponse
from django.views.generic.edit import FormView
from django.utils.translation import get_language
from django.urls import reverse

from itertools import chain
from operator import itemgetter

from haystack.generic_views import FacetedSearchView
from haystack.query import EmptySearchQuerySet, SearchQuerySet
from haystack.inputs import Raw, AutoQuery

from rest_framework import viewsets, serializers, mixins, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.decorators import action

# import rest_framework_filters as filters

from urllib.parse import quote
from urllib.request import urlopen
import codecs, datetime, uuid, base64, zlib, locale, json, requests, random, csv
import pytz

from collections import defaultdict, Counter
from .helpers.mods_xml import initial_response, generate_mods_xml
from .helpers.linked_data import generate_authority_rdf, generate_citation_rdf
from ipware.ip import get_real_ip
import xml.etree.ElementTree as ET

from isisdata.models import *
from isisdata.forms import UserRegistrationForm, UserProfileForm
from curation.forms import UserCitationCollectionForm
from isisdata.templatetags.metadata_filters import get_coins_from_citation
from isisdata import helper_methods
from isisdata.twitter_methods import get_featured_tweet
from isisdata.isiscbviews.authority_views import _get_wikipedia_image_synopsis

from unidecode import unidecode
import datetime


class ReadOnlyLowerField(serializers.ReadOnlyField):
    """
    Coerces value to lowercase.
    """
    def to_representation(self, obj):
        return obj.lower()


class GenericHyperlink(serializers.HyperlinkedRelatedField):
    """
    Handles generic relations.
    """
    view_name = 'generic-detail'

    def get_url(self, obj, v, request, format):
        view_name = type(obj).__name__.lower() + '-detail'
        return super(GenericHyperlink, self).get_url(obj, view_name,
                                                     request, format)


class ValueSerializer(serializers.HyperlinkedModelSerializer):
    value = serializers.ReadOnlyField(source='cvalue')
    value_type = ReadOnlyLowerField(source='child_class')

    class Meta(object):
        model = Value
        fields = ('value', 'value_type')


class ContentTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta(object):
        model = ContentType
        fields = ('url', 'model')


class AttributeTypeSerializer(serializers.HyperlinkedModelSerializer):
    content_type = ContentTypeSerializer(source='value_content_type')

    class Meta(object):
        model = AttributeType
        fields = ('url', 'id', 'name', 'content_type')


class AttributeSerializer(serializers.HyperlinkedModelSerializer):
    type_controlled = AttributeTypeSerializer(many=False)
    source = GenericHyperlink(many=False, read_only=True)
    value = ValueSerializer(many=False, read_only=True)

    class Meta(object):
        model = Attribute
        fields = ('uri', 'url', 'id',
                  'type_controlled',
                  'type_controlled_broad',
                  'source',
                  'value',
                  'value_freeform')


class LanguageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta(object):
        model = Language
        fields = ('url', 'id', 'name')


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta(object):
        model = User
        fields = ('url', 'id', 'username', 'date_joined')


class ContentTypeRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        return value.id

    def to_internal_value(self, data):

        return ContentType.objects.get(pk=data)

class UserRelatedSerializer(serializers.HyperlinkedModelSerializer):
    class Meta(object):
        model = User
        fields = ('id', 'username')

    def to_representation(self, value):
        return super(UserRelatedSerializer, self).to_representation(value)

    def to_internal_value(self, data):
        return User.objects.get(pk=data)
        return super(UserRelatedSerializer, self).to_internal_value(data)


class CommentSerializer(serializers.HyperlinkedModelSerializer):
    subject_content_type = ContentTypeRelatedField(queryset=ContentType.objects.all(), many=False)
    created_by = UserRelatedSerializer(many=False, read_only=True)
    byline = serializers.ReadOnlyField()
    linkified = serializers.ReadOnlyField()
    id = serializers.ReadOnlyField()

    class Meta(object):
        model = Comment
        fields = '__all__'

    def create(self, *args, **kwargs):
        """
        Create a new ``Comment`` instance.
        """

        id = args[0].get('id', None)
        subject_field = args[0].get('subject_field', None)
        subject_content_type = args[0].get('subject_content_type', None)
        subject_instance_id = args[0].get('subject_instance_id', None)
        text = args[0].get('text', None)

        if text and subject_content_type and subject_instance_id:
            instance = Comment(
                text=text,
                subject_field=subject_field,
                subject_content_type=subject_content_type,
                subject_instance_id=subject_instance_id,
                created_by=self._context['request'].user
            )
            instance.save()
        return instance
        # return super(CommentSerializer, self).create(*args, **kwargs)


class LinkedDataTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta(object):
        model = LinkedDataType
        fields = '__all__'


class LinkedDataSerializer(serializers.HyperlinkedModelSerializer):
    type_controlled = LinkedDataTypeSerializer(many=False)
    class Meta(object):
        model = LinkedData
        fields = ('universal_resource_name', 'description', 'type_controlled')


class CCRelationSerializer(serializers.HyperlinkedModelSerializer):
    attributes = AttributeSerializer(many=True, read_only=True)
    linked_data = LinkedDataSerializer(many=True, read_only=True,
                                       source='linkeddata_entries')

    class Meta(object):
        model = CCRelation

        fields = ('uri', 'url', 'id',
                  'subject', 'object',
                  'name',
                  'description',
                  'type_controlled',
                  'attributes',
                  'linked_data')

class CCRelationSparseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta(object):
        model = CCRelation

        fields = ('uri', 'url', 'id',
                  'subject', 'object',
                  'name',
                  'type_controlled')


class ACRelationSerializer(serializers.HyperlinkedModelSerializer):
    attributes = AttributeSerializer(many=True, read_only=True)
    linked_data = LinkedDataSerializer(many=True, read_only=True,
                                       source='linkeddata_entries')

    class Meta(object):
        model = ACRelation

        fields = ('uri', 'url', 'id',
                  'citation', 'authority',
                  'name',
                  'description',
                  'type_controlled',
                  'attributes',
                  'linked_data')


class ACRelationSparseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta(object):
        model = ACRelation

        fields = ('uri', 'url', 'id',
                  'citation', 'authority',
                  'name',
                  'type_controlled')


class AARelationSerializer(serializers.HyperlinkedModelSerializer):
    attributes = AttributeSerializer(many=True, read_only=True)
    linked_data = LinkedDataSerializer(many=True, read_only=True,
                                       source='linkeddata_entries')

    class Meta(object):
        model = AARelation

        fields = ('uri', 'url', 'id',
                  'subject', 'object',
                  'name',
                  'description',
                  'type_controlled',
                  'attributes',
                  'linked_data')


class AARelationSparseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta(object):
        model = AARelation

        fields = ('uri', 'url', 'id',
                  'subject', 'object',
                  'name',
                  'type_controlled')

class AuthoritySearchResultSerializer(serializers.Serializer):
    id = serializers.CharField(required=True, source="pk")
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    #attributes = serializers.ListField(
    #   child=serializers.CharField(required=False)
    #)
    authority_type = serializers.CharField(required=False)

class AuthoritySerializer(serializers.HyperlinkedModelSerializer):
    attributes = AttributeSerializer(many=True, read_only=True)
    linked_data = LinkedDataSerializer(many=True, read_only=True,
                                       source='linkeddata_entries')
    related_citations = ACRelationSparseSerializer(read_only=True, many=True,
                                                   source='acrelations')
    related_authorities = AARelationSparseSerializer(read_only=True, many=True,
                                                     source='aarelations')

    class Meta(object):
        model = Authority
        fields = ('id', 'uri', 'url', 'name',
                  'description',
                  'type_controlled',
                  'classification_system',
                  'classification_code',
                  'classification_hierarchy',
                  'redirect_to',
                  'attributes',
                  'linked_data',
                  'related_citations',
                  'related_authorities')

    def to_representation(self, obj):
        """
        Add Person-specific fields to the instance representation.

        TODO: make this more general.
        """

        repr = super(AuthoritySerializer, self).to_representation(obj)
        if hasattr(obj, 'person'):
            obj = obj.person
            for fname in ['personal_name_last',
                          'personal_name_first',
                          'personal_name_suffix']:
                repr[fname] = getattr(obj, fname)
        return repr


class CitationSerializer(serializers.HyperlinkedModelSerializer):
    language = LanguageSerializer(many=True, read_only=True)
    attributes = AttributeSerializer(many=True, read_only=True)
    linked_data = LinkedDataSerializer(many=True, read_only=True,
                                       source='linkeddata_entries')
    related_citations = CCRelationSparseSerializer(read_only=True, many=True,
                                                   source='ccrelations')
    related_authorities = ACRelationSparseSerializer(read_only=True, many=True,
                                               source='acrelations')

    class Meta(object):
        model = Citation
        fields = ('uri', 'url', 'id',
                  'title',
                  'description',
                  'language',
                  'type_controlled',
                  'abstract',
                  'edition_details',
                  'physical_details',
                  'attributes',
                  'linked_data',
                  'related_citations',
                  'related_authorities')


class PartDetailsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta(object):
        model = PartDetails
        fields = '__all__'


# class AuthorityFilterSet(filters.FilterSet):
#     name = filters.AllLookupsFilter(name='name')
#     class Meta:
#         model = Authority
#         fields = ['name', 'type_controlled']


class AuthorityViewSet(mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       viewsets.GenericViewSet):
    queryset = Authority.objects.all()
    serializer_class = AuthoritySerializer
    # filter_class = AuthorityFilterSet
    # filter_fields = ('name', )

    @action(detail=False)
    def search(self, request, *args, **kwargs):
        query = request.query_params.get("query", '')

        sqs = SearchQuerySet().models(Authority).filter(content=AutoQuery(query), public=True)

        page = self.paginate_queryset(sqs)
        if page is not None:
            serializer = AuthoritySearchResultSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AuthoritySearchResultSerializer(sqs, many=True)
        return Response(serializer.data)


class UserViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated,]


class CitationViewSet(mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      viewsets.GenericViewSet):
    queryset = Citation.objects.all()
    serializer_class = CitationSerializer
    permission_classes = [permissions.IsAuthenticated,]


class ACRelationViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    queryset = ACRelation.objects.all()
    serializer_class = ACRelationSerializer
    permission_classes = [permissions.IsAuthenticated,]


class CCRelationViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    queryset = CCRelation.objects.all()
    serializer_class = CCRelationSerializer
    permission_classes = [permissions.IsAuthenticated,]


class AARelationViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    queryset = AARelation.objects.all()
    serializer_class = AARelationSerializer
    permission_classes = [permissions.IsAuthenticated,]


class AttributeTypeViewSet(mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           viewsets.GenericViewSet):
    queryset = AttributeType.objects.all()
    serializer_class = AttributeTypeSerializer
    pagination_class = None     # Angular has trouble with pagination.
    permission_classes = [permissions.AllowAny,]


class ContentTypeViewSet(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         viewsets.GenericViewSet):
    queryset = ContentType.objects.all()
    serializer_class = ContentTypeSerializer
    permission_classes = [permissions.IsAuthenticated,]


class ValueViewSet(mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   viewsets.GenericViewSet):
    queryset = Value.objects.all()
    serializer_class = ValueSerializer
    permission_classes = [permissions.IsAuthenticated,]


class LanguageViewSet(mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      viewsets.GenericViewSet):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer
    permission_classes = [permissions.IsAuthenticated,]


class AttributeViewSet(mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       viewsets.GenericViewSet):

    queryset = Attribute.objects.all()
    serializer_class = AttributeSerializer
    permission_classes = [permissions.IsAuthenticated,]


class LinkedDataViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    queryset = LinkedData.objects.all()
    serializer_class = LinkedDataSerializer
    permission_classes = [permissions.IsAuthenticated,]


class LinkedDataTypeViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    queryset = LinkedDataType.objects.all()
    serializer_class = LinkedDataTypeSerializer
    permission_classes = [permissions.IsAuthenticated,]


class PartDetailsViewSet(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         viewsets.GenericViewSet):
    queryset = PartDetails.objects.all()
    serializer_class = PartDetailsSerializer
    permission_classes = [permissions.IsAuthenticated,]


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    pagination_class = None     # Angular has trouble with pagination.

    def delete(self, request, *args, **kwargs):
        """
        Users can only delete comments that they themselves have created.
        """
        pk = kwargs.get('pk', None)
        if pk:
            instance = Comment.objects.get(pk=pk)
            if request.user.id != instance.created_by.id:
                return HttpResponseForbidden()
        return super(CommentViewSet, self).delete(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """
        Don't allow users to edit other users' comments.
        """

        pk = kwargs.get('pk', None)
        if pk:
            instance = Comment.objects.get(pk=pk)
            if request.user.id != instance.created_by.id:
                return HttpResponseForbidden()
        return super(CommentViewSet, self).update(request, *args, **kwargs)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True,
                                           context={'request': request})
        return Response(serializer.data)

    def get_queryset(self):
        queryset = super(CommentViewSet, self).get_queryset()
        subject_instance_id = self.request.query_params.get('subject_instance_id', None)
        subject_content_type = self.request.query_params.get('subject_content_type', None)
        if subject_instance_id and subject_content_type:
            queryset = queryset.filter(subject_instance_id=subject_instance_id,
                                       subject_content_type_id=subject_content_type)
        return queryset


@api_view(('GET',))
def api_root(request, format=None):
    return Response({
        'authority': reverse('authority-list', request=request, format=format),
        'citation': reverse('citation-list', request=request, format=format),
        'acrelation': reverse('acrelation-list', request=request, format=format),
        'ccrelation': reverse('ccrelation-list', request=request, format=format),
        'aarelation': reverse('aarelation-list', request=request, format=format),
        'attribute': reverse('attribute-list', request=request, format=format),
        'linkeddata': reverse('linkeddata-list', request=request, format=format),
    })

def index(request):
    context = {
        'test': False,
    }
    return render(request, 'isisdata/index.html', context)


def index(request, obj_id=None):
    if (obj_id == None):
        return render(request, 'isisdata/index.html', {})
    try:
        object = Authority.objects.get(id=obj_id)
    except Authority.DoesNotExist:
        object = None
    if object != None:
        return redirect('authority', authority_id = obj_id)

    return redirect('citation', citation_id = obj_id)


def api_redirect(request, base_view=None, obj_id=None):
    """
    When '.json' is appended to a citation or authority URL, it should redirect
    to the REST API view for that resource.

    TODO: implement redirect for search results.
    """

    view_name = '{model}-detail'.format(model=base_view)
    rest_view = reverse(view_name, args=[obj_id], request=request)
    return HttpResponseRedirect(rest_view)

def help(request):
    """
    View for help page
    """

    return render(request, 'isisdata/help.html', context={'active': 'help'})

def about(request):
    """
    View for about page
    """
    return render(request, 'isisdata/about.html', context={'active': 'about'})

def playground(request):
    """
    View for playground page
    """
    return render(request, 'isisdata/playground.html', context={'active': 'playground'})


def statistics(request):
    """
    View for statistics page
    """

    # set timeout (in sec) to one day
    cache_timeout = 86400

    # cache = caches['default']
    # citations_count = cache.get('statistics_citation')
    # if not citations_count:
    #     citations_count = Citation.objects.filter(public=True).count()
    #     cache.set('statistics_citation', citations_count, cache_timeout)

    # authority_count = cache.get('statistics_authority')
    # if not authority_count:
    #     authority_count = Authority.objects.filter(public=True).count()
    #     cache.set('statistics_authority', authority_count, cache_timeout)
    #
    # acrelation_count = cache.get('statistics_acrelation')
    # if not acrelation_count:
    #     acrelation_count = ACRelation.objects.select_related('citation').select_related('authority').filter(public=True, citation__public=True, authority__public=True).count()
    #     cache.set('statistics_acrelation', acrelation_count, cache_timeout)
    #
    # ccrelation_count = cache.get('statistics_ccrelation')
    # if not ccrelation_count:
    #     ccrelation_count = CCRelation.objects.select_related('subject').select_related('object').filter(public=True, subject__public=True, object__public=True).count()
    #     cache.set('statistics_ccrelation', ccrelation_count, cache_timeout)
    #
    # aarelation_count = cache.get('statistics_aarelation')
    # if not aarelation_count:
    #     aarelation_count = AARelation.objects.select_related('subject').select_related('object').filter(public=True, subject__public=True, object__public=True).count()
    #     cache.set('statistics_aarelation', aarelation_count, cache_timeout)
    #
    # # by curator
    # curator_neu_count = _get_count_by_dataset('curators_neu',"(John Neu, ed.)", cache_timeout)
    # curator_harvey_count = _get_count_by_dataset('curators_harvey',"(Joy Harvey, ed.)", cache_timeout)
    # curator_weldon_count = _get_count_by_dataset('curators_weldon',"(Stephen P. Weldon, ed.)", cache_timeout)
    # curator_moon_count = _get_count_by_dataset('curators_moon',"(Suzanne Moon, ed.)", cache_timeout)
    #
    # # by citation type
    # books_count = _get_count_citation_type('statistics_book', "BO", cache_timeout)
    # articles_count = _get_count_citation_type('statistics_article', "AR", cache_timeout)
    # chapters_count = _get_count_citation_type('statistics_chapter', "CH", cache_timeout)
    # reviews_count = _get_count_citation_type('statistics_review', "RE", cache_timeout)
    # theses_count = _get_count_citation_type('statistics_thesis', "TH", cache_timeout)
    #
    # # by authority type
    # persons_count = _get_count_authority_type('statistics_person', "PE", cache_timeout)
    # institutions_count = _get_count_authority_type('statistics_institution', "IN", cache_timeout)
    # time_periods_count = _get_count_authority_type('statistics_time_period', "TI", cache_timeout)
    # geographic_terms_count = _get_count_authority_type('statistics_geographic_term', "GE", cache_timeout)
    # serial_publications_count = _get_count_authority_type('statistics_serial_publication', "SE", cache_timeout)
    # classification_terms_count = _get_count_authority_type('statistics_classification_term', "CT", cache_timeout)
    # concepts_count = _get_count_authority_type('statistics_concepts', "CO", cache_timeout)
    # creative_works_count = _get_count_authority_type('statistics_creative_work', "CW", cache_timeout)
    # events_count = _get_count_authority_type('statistics_event', "EV", cache_timeout)
    # crossreferences_count = _get_count_authority_type('statistics_crossreference', "CR", cache_timeout)
    # publishers_count = _get_count_authority_type('statistics_publisher', "PU", cache_timeout)

    context = {
        'active': 'about',
        # 'citations_count': citations_count,
        # 'authority_count': authority_count,
        # 'relation_count': acrelation_count + ccrelation_count + aarelation_count,
        # # curators
        # 'curator_neu_count': curator_neu_count,
        # 'curator_harvey_count': curator_harvey_count,
        # 'curator_weldon_count': curator_weldon_count,
        # 'curator_moon_count': curator_moon_count,
        # # citation types
        # 'books_count': books_count,
        # 'articles_count': articles_count,
        # 'chapters_count': chapters_count,
        # 'reviews_count': reviews_count,
        # 'theses_count': theses_count,
        # # authority types
        # 'persons_count': persons_count,
        # 'institutions_count': institutions_count,
        # 'time_periods_count': time_periods_count,
        # 'geographic_terms_count': geographic_terms_count,
        # 'serial_publications_count': serial_publications_count,
        # 'classification_terms_count': classification_terms_count,
        # 'concepts_count': concepts_count,
        # 'creative_works_count': creative_works_count,
        # 'events_count': events_count,
        # 'crossreferences_count': crossreferences_count,
        # 'publishers_count': publishers_count,
    }
    return render(request, 'isisdata/statistics.html', context=context)

def _get_count_citation_type(cache_name, citation_type, cache_timeout):
    cache = caches['default']
    count = cache.get(cache_name)
    if not count:
        count = Citation.objects.filter(public=True, type_controlled=citation_type).count()
        cache.set(cache_name, count, cache_timeout)
    return count

def _get_count_authority_type(cache_name, authority_type, cache_timeout):
    cache = caches['default']
    count = cache.get(cache_name)
    if not count:
        count = Authority.objects.filter(public=True, type_controlled=authority_type).count()
        cache.set(cache_name, count, cache_timeout)
    return count

def _get_count_by_dataset(cache_name, curator_str, cache_timeout):
    cache = caches['default']
    count = cache.get(cache_name)
    if not count:
        ds = Dataset.objects.filter(name__icontains=curator_str)
        # TODO: check that ds is not a list
        citations_count = Citation.objects.filter(belongs_to=ds).count()
        authorities_count = Authority.objects.filter(belongs_to=ds).count()
        count = citations_count + authorities_count
        cache.set(cache_name, count, cache_timeout)
    return count

def citation(request, citation_id):
    """
    View for individual citation record.
    """
    citation = get_object_or_404(Citation, pk=citation_id)

    if not citation.public:
        return HttpResponseForbidden()

    # Some citations are deleted. These should be hidden from public view.
    if citation.status_of_record == Citation.DELETE:
        raise Http404("No such Citation")

    authors = citation.acrelation_set.filter(type_controlled__in=[ACRelation.AUTHOR, ACRelation.CONTRIBUTOR, ACRelation.EDITOR], citation__public=True, public=True)
    author_ids = [author.authority.id for author in authors if author.authority]

    subjects = citation.acrelation_set.filter(Q(type_controlled__in=[ACRelation.SUBJECT], citation__public=True, public=True))
    subject_ids = [subject.authority.id for subject in subjects if subject.authority]

    persons = citation.acrelation_set.filter(type_broad_controlled__in=[ACRelation.PERSONAL_RESPONS], citation__public=True, public=True)
    categories = citation.acrelation_set.filter(Q(type_controlled__in=[ACRelation.CATEGORY]), citation__public=True, public=True)

    query_time = Q(type_controlled__in=['TI'], citation__public=True) | (Q(type_controlled__in=[ACRelation.SUBJECT], citation__public=True) & Q(authority__type_controlled__in=[Authority.TIME_PERIOD], citation__public=True))
    time_periods = citation.acrelation_set.filter(query_time).filter(public=True)

    query_places = Q(type_controlled__in=[ACRelation.SUBJECT], citation__public=True) & Q(authority__type_controlled__in=[Authority.GEOGRAPHIC_TERM], citation__public=True)
    places = citation.acrelation_set.filter(query_places).filter(public=True)

    query_concepts = Q(type_controlled__in=[ACRelation.SUBJECT], citation__public=True) & Q(authority__type_controlled__in=[Authority.CONCEPT], citation__public=True)
    concepts = citation.acrelation_set.filter(query_concepts).filter(public=True)

    query_institutions = Q(type_controlled__in=[ACRelation.SUBJECT], citation__public=True) & Q(authority__type_controlled__in=[Authority.INSTITUTION], citation__public=True)
    institutions = citation.acrelation_set.filter(query_institutions).filter(public=True)

    query_people = Q(type_controlled__in=[ACRelation.SUBJECT], citation__public=True) & Q(authority__type_controlled__in=[Authority.PERSON], citation__public=True)
    people = citation.acrelation_set.filter(query_people).filter(public=True)

    related_citations_ic = CCRelation.objects.filter(subject_id=citation_id, type_controlled=CCRelation.INCLUDES_CHAPTER, object__public=True).filter(public=True)
    related_citations_inv_ic = CCRelation.objects.filter(object_id=citation_id, type_controlled=CCRelation.INCLUDES_CHAPTER, subject__public=True).filter(public=True)
    related_citations_isa = CCRelation.objects.filter(subject_id=citation_id, type_controlled=CCRelation.INCLUDES_SERIES_ARTICLE, object__public=True).filter(public=True)
    related_citations_inv_isa = CCRelation.objects.filter(object_id=citation_id, type_controlled=CCRelation.INCLUDES_SERIES_ARTICLE, subject__public=True).filter(public=True)

    query = Q(subject_id=citation_id, type_controlled=CCRelation.REVIEW_OF, object__public=True) | Q(object_id=citation_id, type_controlled=CCRelation.REVIEWED_BY, subject__public=True)
    related_citations_ro = CCRelation.objects.filter(query).filter(public=True)

    related_citations_rb = CCRelation.objects.filter(subject_id=citation_id, type_controlled=CCRelation.REVIEWED_BY, object__public=True).filter(public=True)
    related_citations_re = CCRelation.objects.filter(subject_id=citation_id, type_controlled=CCRelation.RESPONDS_TO, object__public=True).filter(public=True)
    related_citations_inv_re = CCRelation.objects.filter(object_id=citation_id, type_controlled=CCRelation.RESPONDS_TO, subject__public=True).filter(public=True)
    as_query = Q(subject_id=citation_id, type_controlled=CCRelation.ASSOCIATED_WITH, object__public=True) | Q(object_id=citation_id, type_controlled=CCRelation.ASSOCIATED_WITH, object__public=True)
    related_citations_as = CCRelation.objects.filter(as_query).filter(public=True)

    # Similar Citations Generator
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
        similar_citations = results.filter(subject_ids__in=subject_ids).exclude(id=citation_id).query.get_results()

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
        similar_citations = mlt.all().exclude(public="false").query.get_results()
    else:
        similar_citations = []
        word_cloud_results = EmptySearchQuerySet()

    # if authors and len(authors) > 1:
    #     word_cloud_results = results.filter(all_contributor_ids__in=author_ids)
    #     subject_ids_facet, related_contributors_facet, related_institutions_facet, related_geographics_facet, related_timeperiod_facet, related_categories_facet, related_other_person_facet, related_publisher_facet, related_journal_facet, related_subject_concepts_facet, related_subject_people_facet, related_subject_institutions_facet = get_facets(word_cloud_results)
    # else:
    #     word_cloud_results = results
    #     subject_ids_facet, related_contributors_facet, related_institutions_facet, related_geographics_facet, related_timeperiod_facet, related_categories_facet, related_other_person_facet, related_publisher_facet, related_journal_facet, related_subject_concepts_facet, related_subject_people_facet, related_subject_institutions_facet = get_facets(word_cloud_results)

    similar_objects = get_facets_from_similar_citations(similar_citations)

    googleBooksImage = get_google_books_image(citation, False)

    properties = citation.acrelation_set.exclude(type_controlled__in=[ACRelation.AUTHOR, ACRelation.CONTRIBUTOR, ACRelation.EDITOR, ACRelation.SUBJECT, ACRelation.CATEGORY]).filter(public=True)
    properties_map = defaultdict(list)
    for prop in properties:
        properties_map[prop.type_controlled] += [prop]

    # Location of citation in REST API
    api_view = reverse('citation-detail', args=[citation.id], request=request)

    # Provide progression through search results, if present.

    # make sure we have a session key
    if hasattr(request, 'session') and not request.session.session_key:
        request.session.save()
        request.session.modified = True

    session_id = request.session.session_key
    fromsearch = request.GET.get('fromsearch', False)
    #search_key = request.session.get('search_key', None)
    last_query = request.GET.get('last_query', None) #request.session.get('last_query', None)

    query_string = request.GET.get('query_string', None)

    if query_string:
        query_string = quote(query_string) #query_string.encode('ascii','ignore')
        search_key = base64.b64encode(bytes(last_query, 'utf-8'))
        # search_key = base64.b64encode(query_string) #request.session.get('search_key', None)
    else:
        search_key = None

    user_cache = caches['default']
    search_results = user_cache.get('search_results_citation_' + str(search_key))
    page_citation = user_cache.get(session_id + '_page_citation', None) #request.session.get('page_citation', None)

    if search_results and fromsearch and page_citation:

        search_count = search_results.count()

        prev_search_result = None
        # Only display the "previous" link if we are on page 2+.
        if page_citation > 1:
            prev_search_result = search_results[(page_citation - 1)*20 - 1]

        # If we got to the last result of the previous page we need to count
        #  down the page number.
        if prev_search_result == 'isisdata.citation.' + citation_id:
            page_citation = page_citation - 1
            user_cache.set(session_id + '_page_citation', page_citation)
        search_results_page = search_results[(page_citation - 1)*20:page_citation*20 + 2]
        try:
            search_index = search_results_page.index(citation_id) + 1   # +1 for display.
            if search_index == 21:
                user_cache.set(session_id + '_page_citation', page_citation+1)

        except (IndexError, ValueError):
            search_index = None
        try:
            search_next = search_results_page[search_index]
        except (IndexError, ValueError, TypeError):
            search_next = None
        try:
            search_previous = search_results_page[search_index - 2]
            if search_index - 2 == -1:
                search_previous = prev_search_result

        except (IndexError, ValueError, AssertionError, TypeError):
            search_previous = None
        if search_index:
            search_current = search_index + (20* (page_citation - 1))
        else:
            search_current = None
    else:
        search_index = None
        search_next = None
        search_previous = None
        search_current = None
        search_count = 0

    #last_query = request.session.get('last_query', None)

    context = {
        'citation_id': citation_id,
        'citation': citation,
        'authors': authors,
        'properties_map': properties,
        'subjects': subjects,
        'concepts': concepts,
        'persons': persons,
        'categories': categories,
        'people': people,
        'time_periods': time_periods,
        'places': places,
        'institutions': institutions,
        'source_instance_id': citation_id,
        'source_content_type': ContentType.objects.get(model='citation').id,
        'related_citations_ic': related_citations_ic,
        'related_citations_inv_ic': related_citations_inv_ic,
        'related_citations_rb': related_citations_rb,
        'related_citations_isa': related_citations_isa,
        'related_citations_inv_isa': related_citations_inv_isa,
        'related_citations_ro': related_citations_ro,
        'related_citations_re': related_citations_re,
        'related_citations_inv_re': related_citations_inv_re,
        'related_citations_as': related_citations_as,
        'api_view': api_view,
        'search_results': search_results,
        'search_index': search_index,
        'search_next': search_next,
        'search_previous': search_previous,
        'search_current': search_current,
        'search_count': search_count,
        'fromsearch': fromsearch,
        'last_query': last_query,
        'query_string': query_string,
        'similar_citations': similar_citations,
        'cover_image': googleBooksImage,
        'similar_objects': similar_objects,
    }
    return render(request, 'isisdata/citation.html', context)

def get_facets_from_similar_citations(similar_citations):
    similar_objects = defaultdict(list)

    if similar_citations:
        similar_citations_ids = [citation.id for citation in similar_citations]
        similar_citations_qs = Citation.objects.all().filter(id__in=similar_citations_ids)
        similar_acrelations = [acr for similar_citation in similar_citations_qs for acr in similar_citation.acrelations.all()]
        for acrelation in similar_acrelations:
            if acrelation.type_broad_controlled in [acrelation.PERSONAL_RESPONS, acrelation.INSTITUTIONAL_HOST, acrelation.PUBLICATION_HOST]:
                similar_objects[acrelation.type_broad_controlled].append(acrelation.authority)
            if acrelation.type_broad_controlled == acrelation.SUBJECT_CONTENT and acrelation.authority and acrelation.authority.type_controlled:
                similar_objects[acrelation.authority.type_controlled].append(acrelation.authority)

    if similar_objects:
        similar_objects = generate_similar_facets(similar_objects)

    return similar_objects

def generate_similar_facets(similar_objects):
    for key in similar_objects:
        authorities_count = Counter(similar_objects[key])
        similar_facets = []

        for authority in authorities_count:
            similar_facets.append({'authority':authority, 'count':authorities_count[authority]})
        similar_facets = sorted(similar_facets, key=itemgetter('count'), reverse=True)

        similar_objects[key] = similar_facets

    return similar_objects

def get_google_books_image(citation, featured):

    # Provide image for citation
    if citation.type_controlled not in [Citation.BOOK, Citation.CHAPTER]:
        return {}

    cover_image = {}

    parent_id = None
    parent_relations = CCRelation.objects.filter(object_id=citation.id, type_controlled='IC')
    if parent_relations and parent_relations[0].subject:
        parent_id = parent_relations[0].subject.id

    if citation.type_controlled in [Citation.CHAPTER] and parent_id:
        google_books_data = GoogleBooksData.objects.filter(citation__id=parent_id, image_size="standard").first()
    else:
        google_books_data = GoogleBooksData.objects.filter(citation__id=citation.id, image_size="standard").first()

    google_books_refresh_time = settings.GOOGLE_BOOKS_REFRESH_TIME

    # If we have the google books data cached, we can just return the cached data
    if google_books_data and (datetime.datetime.now(datetime.timezone.utc) - google_books_data.last_modified).days < google_books_refresh_time and not featured:
        cover_image['size'] = google_books_data.image_size
        cover_image['url'] = google_books_data.image_url

        return cover_image

    contrib = ''
    title = ''

    if citation.type_controlled in [Citation.BOOK]:
        title = citation.title
        if citation.get_all_contributors and citation.get_all_contributors[0].authority and citation.get_all_contributors[0].authority.name:
            contrib = citation.get_all_contributors[0].authority.name.strip()
    elif citation.type_controlled in [Citation.CHAPTER] and parent_relations and parent_relations[0].subject and parent_relations[0].subject.title:
        title = parent_relations[0].subject.title
        if parent_relations[0].subject.get_all_contributors and parent_relations[0].subject.get_all_contributors[0].authority and parent_relations[0].subject.get_all_contributors[0].authority.name:
            contrib = parent_relations[0].subject.get_all_contributors[0].authority.name.strip()
    if not title:
        return

    if ',' in contrib:
        contrib = contrib[:contrib.find(',')]
    elif ' ' in contrib:
        contrib = contrib[contrib.find(' '):]

    apiKey = settings.GOOGLE_BOOKS_API_KEY

    url = settings.GOOGLE_BOOKS_TITLE_QUERY_PATH.format(title=title, apiKey=apiKey)
    url = url.replace(" ", "%20")

    with requests.get(url) as resp:
        if resp.status_code != 200:
            return {}

        books = resp.json()
        items = books["items"]

    bookGoogleId = ''

    for i in items:
        if i["volumeInfo"]["title"].lower() in title.lower() or 'authors' in i["volumeInfo"] and any(contrib in s for s in i["volumeInfo"]["authors"]):
            bookGoogleId = i["id"]
            break

    if not bookGoogleId:
        return {}

    url2 = settings.GOOGLE_BOOKS_ITEM_GET_PATH.format(bookGoogleId=bookGoogleId, apiKey=apiKey)
    url2 = url2.replace(" ", "%20")

    with urlopen(url2) as response:
        book = json.load(response)

        if 'imageLinks' in book["volumeInfo"]:
            imageLinks = book["volumeInfo"]["imageLinks"].keys()

            if "medium" in imageLinks and not featured:
                cover_image["size"] = "standard"
                cover_image["url"] = book["volumeInfo"]["imageLinks"]["medium"].replace("http://", "https://")
            elif "small" in imageLinks and not featured:
                cover_image["size"] = "standard"
                cover_image["url"] = book["volumeInfo"]["imageLinks"]["thumbnail"].replace("http://", "https://")
            elif "thumbnail" in imageLinks:
                cover_image["size"] = "thumbnail"
                cover_image["url"] = book["volumeInfo"]["imageLinks"]["thumbnail"].replace("http://", "https://")

            if citation.type_controlled in [Citation.BOOK]:
                google_books_data = GoogleBooksData(image_url=cover_image['url'], image_size=cover_image['size'], citation_id=citation.id)
            elif citation.type_controlled in [Citation.CHAPTER] and parent_id:
                google_books_data = GoogleBooksData(image_url=cover_image['url'], image_size=cover_image['size'], citation_id=parent_id)
            google_books_data.save()

            

    return cover_image

@login_required
def search_saved(request):
    """
    Provides saved searches for a logged-in user.
    """

    # If the user is Anonymous, redirect them to the login view.
    if not type(request.user._wrapped) is User:
        return HttpResponseRedirect(reverse('login'))

    save = request.GET.get('save', None)
    remove = request.GET.get('remove', None)
    if save:
        instance = SearchQuery.objects.get(pk=save)
        instance.saved = True
        instance.save()
    if remove:
        instance = SearchQuery.objects.get(pk=remove)
        instance.saved = False
        instance.save()

    searchqueries = request.user.searches.filter(saved=True).order_by('-created_on')

    paginator = Paginator(searchqueries, 10)

    page = request.GET.get('page')
    try:
        searchqueries = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        searchqueries = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        searchqueries = paginator.page(paginator.num_pages)

    context = {
        'searchqueries': searchqueries,
    }
    return render(request, 'isisdata/search_saved.html', context)


@login_required
def search_history(request):
    """
    Provides the search history for a logged-in user.
    """

    # If the user is Anonymous, redirect them to the login view.
    if not type(request.user._wrapped) is User:
        return HttpResponseRedirect(reverse('login'))

    searchqueries = request.user.searches.order_by('-created_on')

    paginator = Paginator(searchqueries, 10)

    page = request.GET.get('page')
    try:
        searchqueries = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        searchqueries = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        searchqueries = paginator.page(paginator.num_pages)

    context = {
        'searchqueries': searchqueries,
    }
    return render(request, 'isisdata/search_history.html', context)


class IsisSearchView(FacetedSearchView):
    """
    Provides the search view at /isis/.
    """

    results_per_page = 20

    def get_form_kwargs(self):
        """
        For some reason GET data isn't getting added to form kwargs, so we do
        it here.
        """
        kwargs = super(IsisSearchView, self).get_form_kwargs()
        if 'data' not in kwargs:
            kwargs['data'] = self.request.GET
            kwargs['searchqueryset'] = self.queryset
        return kwargs

    def form_valid(self, form):
        """
        Overridden to provide search history log functionality.
        """

        page_citation = self.request.GET.get('page_citation', 1)
        page_authority = self.request.GET.get('page_authority', 1)

        # self.request = request
        # self.form = self.build_form()
        # self.query = self.get_query()

        # !! Why are we using strings rather than bools?
        log = self.request.GET.get('log', 'True') != 'False'

        # These are used to generate a SearchQuery instance.
        parameters = self.request.GET.get('q', None)

        # The search query should be ASCII-normalized.
        # TODO: this could be tightened up.
        if parameters:
            parameters = unidecode(parameters)
        q = form.cleaned_data.get('q')
        if q:
            form.cleaned_data['q'] = unidecode(q)

        search_models = self.request.GET.get('models', None)
        selected_facets = self.request.GET.get('selected_facets', None)
        excluded_facets = self.request.GET.get('excluded_facets', None)

        sort_field_citation = self.request.GET.get('sort_order_citation', None)
        sort_order_citation = self.request.GET.get('sort_order_dir_citation', None)
        sort_field_authority = self.request.GET.get('sort_order_authority', None)
        sort_order_authority = self.request.GET.get('sort_order_dir_authority', None)

        # If the user is logged in, attempt to save the search in their
        #  search history.
        if log and parameters and self.request.user.id and self.request.user.id > 0:
            searchquery = SearchQuery(
                user = self.request.user._wrapped,
                parameters = parameters,
                search_models = search_models,
                selected_facets = selected_facets,
            )
            searchquery.save()
            # make sure we have a session key
            if hasattr(self.request, 'session') and not self.request.session.session_key:
                self.request.session.save()
                self.request.session.modified = True

            session_id = self.request.session.session_key
            user_cache = caches['default']
            user_cache.set(session_id + '_last_query', self.request.get_full_path())
            #request.session['last_query'] = request.get_full_path()

        # Used to identify the current search for retrieval from the cache.
        cache_key = u'{0}_{1}_{2}_{3}_{4}_{5}_{6}_{7}'.format(parameters, search_models, selected_facets, excluded_facets, sort_field_citation, sort_order_citation, sort_field_authority, sort_order_authority)

        # 'search_results_cache' is the database cache
        #  (see production_settings.py).
        user_cache = caches['default']
        # Disabling cache for the search itself, for now.
        self.queryset = None #user_cache.get(cache_key)

        if not self.queryset:
            # Perform the search, and store the results in the cache.
            # self.results = self.get_results()
            self.queryset = form.search()
            # Disabling cache for the search itself, for now.
            # user_cache.set(cache_key, self.queryset, 3600)

        # self.results = self.queryset
        # This code sets up cached data to support the search result progression
        #  feature in the citation and authority detail views. It is independent
        #  of the search cacheing above, which is just for performance.
        if parameters:  # Store results in the session cache.
            search_key = base64.b64encode(self.request.get_full_path().encode('ascii', 'ignore'))

            # make sure we have a session key
            if hasattr(self.request, 'session') and not self.request.session.session_key:
                self.request.session.save()
                self.request.session.modified = True
            session_id = self.request.session.session_key

            user_cache.set(session_id + '_search_key', search_key)
            user_cache.set(session_id + '_page_citation', int(page_citation))
            user_cache.set(session_id + '_page_authority', int(page_authority))


            user_cache.set('search_results_authority_' + str(search_key), self.queryset['authority'].values_list('id', flat=True), 3600)
            user_cache.set('search_results_citation_' + str(search_key), self.queryset['citation'].values_list('id', flat=True), 3600)

        context = self.get_context_data(**{
            # self.form_name: form,
        })

        user_playlists = CitationCollection.objects.filter(createdBy=self.request.user.id)

        context.update({'user_playlists': user_playlists})

        return self.render_to_response(context)

    def build_page(self):
        """
        From haystacks SearchView:
        Paginates the results appropriately.
        In case someone does not want to use Django's built-in pagination, it
        should be a simple matter to override this method to do what they would
        like.
        """

        try:
            page_no_authority = int(self.request.GET.get('page_authority', 1))
        except (TypeError, ValueError):
            raise Http404("Not a valid number for page.")

        try:
            page_no_citation= int(self.request.GET.get('page_citation', 1))
        except (TypeError, ValueError):
            raise Http404("Not a valid number for page.")

        if page_no_authority < 1:
            raise Http404("Pages should be 1 or greater.")

        if page_no_citation < 1:
            raise Http404("Pages should be 1 or greater.")

        start_offset_authority = (page_no_authority - 1) * self.results_per_page
        start_offset_citation = (page_no_citation - 1) * self.results_per_page

        if isinstance(self.queryset, EmptySearchQuerySet):
            self.queryset[0:self.results_per_page]
            paginator_authority = Paginator(self.queryset, self.results_per_page)
            paginator_citation = Paginator(self.queryset, self.results_per_page)

        else:
            self.queryset['citation'][start_offset_citation:start_offset_citation + self.results_per_page]
            self.queryset['authority'][start_offset_authority:start_offset_authority+ self.results_per_page]

            paginator_authority = Paginator(self.queryset['authority'], self.results_per_page)
            paginator_citation = Paginator(self.queryset['citation'], self.results_per_page)


        try:
            page_authority = paginator_authority.page(page_no_authority)
        except InvalidPage:
            try:
                page_authority = paginator_authority.page(1)
            except InvalidPage:
                raise Http404("No such page!")

        try:
            page_citation = paginator_citation.page(page_no_citation)
        except InvalidPage:
            try:
                page_citation = paginator_citation.page(1)
            except InvalidPage:
                raise Http404("No such page!")

        return ({'authority':paginator_authority, 'citation':paginator_citation}, {'authority':page_authority, 'citation':page_citation})

    def get_context_data(self, **kwargs):
        if 'form' not in kwargs:
            kwargs['form'] = self.get_form()
        if 'view' not in kwargs:
            kwargs['view'] = self
        kwargs.update(self.extra_context())
        return kwargs

    def get_queryset(self):
        """
        Faceting happens (for now, at least) in the search form, and NOT in the
        view. So we overwrite this method to prevent faceting again. Or other
        weird things.

        TODO: consider moving the faceting logic to this method? Or somewhere
        else in the view?
        """
        return self.queryset

    def extra_context(self):
        # extra = super(FacetedSearchView, self).extra_context()
        extra = {}
        extra['request'] = self.request

        paginator, page = self.build_page()
        extra['show_publisher_types'] = [dict(Citation.TYPE_CHOICES)[Citation.BOOK], dict(Citation.TYPE_CHOICES)[Citation.CHAPTER]]
        extra['show_school_types'] = [dict(Citation.TYPE_CHOICES)[Citation.THESIS]]
        extra['page'] = page
        extra['paginator'] = paginator
        extra['query'] = self.request.GET.get('q', '')

        if isinstance(self.queryset, EmptySearchQuerySet):
            extra['facets_citation'] = 0
            extra['facets_authority'] = 0
            extra['count_citation'] = len(self.queryset)
            extra['count_authority'] = len(self.queryset)
        else:
            extra['facets_authority'] = self.queryset['authority'].facet_counts()
            extra['facets_citation'] = self.queryset['citation'].facet_counts()
            extra['count_citation'] = len(self.queryset['citation'])
            extra['count_authority'] = len(self.queryset['authority'])

        extra['models'] = self.request.GET.getlist('models')
        extra['sort_order_citation'] = self.request.GET.get('sort_order_citation')
        extra['sort_order_authority'] = self.request.GET.get('sort_order_authority')
        extra['sort_order_dir_citation'] = self.request.GET.get('sort_order_dir_citation')
        extra['sort_order_dir_authority'] = self.request.GET.get('sort_order_dir_authority')

        # we need to change something about this, this is terrible...
        # but it works
        if not extra['sort_order_dir_citation'] and (not extra['sort_order_citation'] or 'publication_date_for_sort' in extra['sort_order_citation']):
            extra['sort_order_dir_citation'] = 'descend'

        if not extra['sort_order_dir_authority']:
            extra['sort_order_dir_authority'] = 'ascend'

        extra['active'] = 'home'

        # create authorities facets
        facet_map = {}
        facets_raw = []
        for facet in self.request.GET.getlist("selected_facets"):
            if ":" not in facet:
                continue

            field, value = facet.split(":", 1)

            if value:
                facet_map.setdefault(field, []).append(value)
                facets_raw.append(field + ":" + quote(codecs.encode(value,'utf-8')))

        extra['selected_facets'] = facet_map
        extra['selected_facets_raw'] = facets_raw

        # add excluded facets
        excluded_facets_map = {}
        excluded_facets_raw = []
        for facet in self.request.GET.getlist("excluded_facets"):
            if ":" not in facet:
                continue

            field, value = facet.split(":", 1)

            if value:
                excluded_facets_map.setdefault(field, []).append(value)
                excluded_facets_raw.append(field + ":" + quote(codecs.encode(value,'utf-8')))

        extra['excluded_facets'] = excluded_facets_map
        extra['excluded_facets_raw'] = excluded_facets_raw

        return extra


# class UserPasswordResetView(FormView):
#     form_class = UserPasswordResetView
#     template_name = 'registration/password_reset_form.html'



class UserRegistrationView(FormView):
    form_class = UserRegistrationForm
    template_name = 'registration/registration_form.html'

    def get_initial(self):
        initial = super(UserRegistrationView, self).get_initial()
        initial.update({'next': self.request.GET.get('next', None)})
        return initial

    def register(self, **cleaned_data):
        new_user = User.objects.create_user(cleaned_data['username'],
                                 cleaned_data['email'],
                                 cleaned_data['password1'])
        profile = UserProfile()
        profile.user = new_user
        profile.save()

        # Automatically log the user in.
        user = authenticate(username=cleaned_data['username'],
                            password=cleaned_data['password1'])
        if user.is_active:
            login(self.request, user)

        return cleaned_data['next']

    def form_valid(self, form):
        """
        If the form is valid, register the user and proceed to the next page.
        """
        next = self.get_success_url(self.register(**form.cleaned_data))
        return HttpResponseRedirect(next)

    def post(self, request, *args, **kwargs):
            """
            Handles POST requests, instantiating a form instance with the passed
            POST variables and then checked for validity.
            """
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)

    def get_success_url(self, next):
        if next is not None and next != '':
            return next
        return '/'


def unapi_server_root(request):
    id = request.GET.get('id', '')
    format = request.GET.get('format', '')
    if id and format:
        citation = get_object_or_404(Citation, pk=id)
        return HttpResponse(generate_mods_xml(citation), content_type="application/xml")
    if id:
        return HttpResponse(initial_response(id))

    return HttpResponse('')



def home(request):
    """
    The landing view, at /.
    """
    # Get featured citation and authority
    now = datetime.datetime.now(pytz.timezone(settings.ADMIN_TIMEZONE))
    current_featured_authorities = FeaturedAuthority.objects.filter(start_date__lt=now).filter(end_date__gt=now)
    current_featured_authority_ids = [featured_authority.authority.id for featured_authority in current_featured_authorities]
    featured_authorities = Authority.objects.filter(id__in=current_featured_authority_ids).exclude(wikipediadata__intro='')

    sqs = SearchQuerySet().models(Citation)
    sqs.query.set_limits(low=0, high=30)
    # featured_citations = sqs.all().exclude(public="false").filter(abstract = Raw("[* TO *]")).filter(title = Raw("[* TO *]")).query.get_results()
    featured_citations = sqs.all().exclude(public="false")
    featured_citations = featured_citations.filter(subject_ids__in=current_featured_authority_ids).filter(type__in=['Book', 'Article']).filter(abstract = Raw("[* TO *]")).filter(title = Raw("[* TO *]")).query.get_results()

    if featured_citations:
        featured_citation = featured_citations[random.randint(0,len(featured_citations)-1)]
        featured_citation = Citation.objects.filter(pk=featured_citation.id).first()
    else:
        #set default featured citation in case no featured authorities have been selected
        featured_citation = Citation.objects.filter(pk=settings.FEATURED_CITATION_ID).first()

    featured_citation_authors = featured_citation.acrelation_set.filter(type_controlled__in=[ACRelation.AUTHOR, ACRelation.CONTRIBUTOR, ACRelation.EDITOR], citation__public=True, public=True)
    featured_citation_image = get_google_books_image(featured_citation, True)

    if featured_authorities:
        featured_authority = featured_authorities[random.randint(0,len(featured_authorities)-1)]
    else:
        #set default featured authorities in case no featured authorities have been selected
        featured_authority = Authority.objects.filter(pk=settings.FEATURED_AUTHORITY_ID).first()

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
    wikiImage, wikiIntro, wikiCredit = _get_wikipedia_image_synopsis(featured_authority, author_contributor_count, related_citations_count)

    #Get featured tweet
    recent_tweet_url, recent_tweet_text, recent_tweet_image = get_featured_tweet()

    properties = featured_citation.acrelation_set.exclude(type_controlled__in=[ACRelation.AUTHOR, ACRelation.EDITOR, ACRelation.CONTRIBUTOR, ACRelation.SUBJECT, ACRelation.CATEGORY]).filter(public=True)

    start_index = 0
    end_index = 10
    recent_records =[]

    # unfortunately, citatations freshly created are public=False so we can't filter on that field when retrieving
    # creation events, we have to test that after we got the real object form the history object
    while len(recent_records) < 10:
        recent_citations = Citation.history.filter(history_type="+").order_by('-history_date')[start_index:end_index]
        recent_authorities = Authority.history.filter(history_type="+").order_by('-history_date')[start_index:end_index]

        for record in sorted(chain(recent_citations, recent_authorities), key=lambda rec: rec.history_date, reverse=True):
            try:
                record = Citation.objects.get(pk=record.id) if type(record) is HistoricalCitation else Authority.objects.get(pk=record.id)
                if record.public:
                    recent_records.append(record)
            except Exception as e:
                print(e)

    context = {
        'active': 'home',
        'records_recent': recent_records[:10],
        'comments_recent': Comment.objects.order_by('-modified_on')[:10],
        'citation': featured_citation,
        'featured_citation_authors': featured_citation_authors,
        'featured_authority': featured_authority,
        'featured_citation_image': featured_citation_image,
        'wikiImage': wikiImage,
        'wikiCredit': wikiCredit,
        'wikiIntro': wikiIntro,
        'properties_map': properties,
        'tweet_text': recent_tweet_text,
        'tweet_url': recent_tweet_url,
        'tweet_image': recent_tweet_image,
    }
    return render(request, 'isisdata/home.html', context=context)


def rdf_authority_view(request, authority_id):
    """
    Get RDF for citations
    """

    if authority_id:
        authority = get_object_or_404(Authority, pk=authority_id)
        return HttpResponse(generate_authority_rdf(authority), content_type="text/rdf+xml")

    return HttpResponse('')


def rdf_citation_view(request, citation_id):
    """
    Get RDF for authorities
    """

    if citation_id:
        citation = get_object_or_404(Citation, pk=citation_id)
        return HttpResponse(generate_citation_rdf(citation), content_type="text/rdf+xml")

    return HttpResponse('')


def api_documentation(request):
    """
    Information page about the REST API.
    """

    rest_endpoint = request.build_absolute_uri(reverse('rest_root'))
    context = {
        'active': 'about',
        'rest_endpoint': rest_endpoint,
    }
    return render(request, 'isisdata/api.html', context)


def build_openurl(endpoint, citation):
    coins = get_coins_from_citation(citation)
    return  endpoint + '?' + coins


def get_linkresolver_url_by_ip(request, citation):
    """
    Use the WorldCat registry API to get the appropriate OpenURL resolver for
    the user, based on their IP address.
    """

    worldcat_registry = "http://www.worldcat.org/registry/lookup?IP={ip}"
    worldcat_tag = "{http://worldcatlibraries.org/registry/resolver}"


    user_ip = get_real_ip(request)
    # user_ip = "149.169.132.43"
    response = urlopen(worldcat_registry.format(ip=user_ip)).read()

    root = ET.fromstring(response)
    resolver = root.find('.//' + worldcat_tag + 'resolver')

    if resolver:
        url = build_openurl(resolver.find(worldcat_tag + 'baseURL').text.strip(), citation)
        linkIcon = getattr(resolver.find(worldcat_tag + 'linkIcon'), 'text', '').strip()
        linkText = getattr(resolver.find(worldcat_tag + 'linkText'), 'text', '').strip()
        return {
            'url': url,
            'icon': linkIcon,
            'text': linkText,
        }
    return


def get_linkresolver_url(request, citation_id):
    citation = get_object_or_404(Citation, pk=citation_id)
    data = None
    if request.user.id and request.user.id > 0:
        if request.user.profile.resolver_institution:
            resolver = request.user.profile.resolver_institution.resolver
            data = {
                'url':  build_openurl(resolver.endpoint, citation),
                'icon': resolver.link_icon,
                'text': resolver.link_text,
            }
    else:
        # If the user is not logged in, or has not selected a link resolver, we can
        #  attempt to find their resolver by IP address.
        data = get_linkresolver_url_by_ip(request, citation)
    if not data:
        data = {'url': '', 'icon': '', 'text': ''}
    return JsonResponse(data)


def user_profile(request, username):
    """
    Each user has a profile page that displays some basic information about
    them, as well as their recent comments. Eventually this will display
    other related content (shared bookmarks, claimed authority record, etc).
    """
    user = get_object_or_404(User, username=username)
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile()
        profile.user = user
        profile.save()

    edit = request.GET.get('edit')

    recent_collections = CitationCollection.objects.filter(createdBy=user).order_by('-created')[:3]

    searchqueries = request.user.searches.order_by('-created_on')

    # Only the owner of the profile can change it. We use a regular Form rather
    #  than a ModelForm because some fields belong to User and other fields
    #  belong to UserProfile.
    form_error = False
    if request.method == 'POST' and request.user.id == user.id:
        form = UserProfileForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data    # Easier to write.
            user.first_name = data.get('first_name')
            user.last_name = data.get('last_name')
            user.email = data.get('email')
            user.profile.affiliation = data.get('affiliation')
            user.profile.location = data.get('location')
            user.profile.bio = data.get('bio')    # Assings to bio.raw.
            user.profile.share_email = data.get('share_email')
            user.profile.resolver_institution = data.get('resolver_institution')
            user.save()
            user.profile.save()
        else:
            form_error = True

    comments = Comment.objects.filter(created_by=user).order_by('-created_on')
    context = {
        'active': '',
        'username': user.username,
        'full_name': '%s %s' % (user.first_name, user.last_name),
        'is_staff': user.is_staff,
        'email': user.email,
        'profile': user.profile,
        'usercomments': comments,
        'recent_collections': recent_collections,
    }

    # User has elected to edit their own profile.
    if edit and user.id == request.user.id:
        # This template has an almost identical layout to userprofile.html,
        #  except that display fields are replaced with input fields.
        template = 'isisdata/userprofile_edit.html'
        form = UserProfileForm(initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'affiliation': getattr(user.profile, 'affiliation', None),
            'location': getattr(user.profile, 'location', None),
            'bio': user.profile.bio.raw,    # Raw markdown.
            'share_email': user.profile.share_email,
            'resolver_institution': user.profile.resolver_institution,
        })
        context.update({'form': form})
    elif form_error:
        context.update({'form': form})
        template = 'isisdata/userprofile_edit.html'
    else:
        template = 'isisdata/userprofile.html'
    return render(request, template, context)

def user_playlists(request, username):
    user = get_object_or_404(User, username=username)

    collections = CitationCollection.objects.filter(createdBy=user).order_by('-created')
    context = {
        'collections': collections,
        'username': user.username,
    }
    template = 'isisdata/user_playlists.html'
    return render(request, template, context)

def playlist(request, *args, **kwargs):
    user = request.user
    edit = request.GET.get('edit')
    collection_id = kwargs.get('collection_id')
    collection = get_object_or_404(CitationCollection, id=collection_id)
    citation_ids = [citation.id for citation in collection.citations.all()]
    citations = Citation.objects.filter(pk__in=citation_ids)
    facets = get_facets_from_similar_citations(citations)
    for citation in citations:
        citation.cover_image = get_google_books_image(citation, False)
        if not citation.cover_image:
            citation.cover_image = {'url': 'https://upload.wikimedia.org/wikipedia/commons/e/e3/Hieroglyphs-temple-Ombos-Egypt.jpg'}

    # Only the owner of the collection can change it. 
    form_error = False
    if request.method == 'POST' and request.user.id == user.id:
        form = UserCitationCollectionForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            collection.name = data.get('name')
            collection.description = data.get('description')
            collection.coverimage_url = data.get('coverimage_url')
            collection.save()
        else:
            form_error = True

    context = {
        'user': user,
        'collection': collection,
        'citations': citations,
        'subjects': collection.subjects.all(),
        'facets': facets,
    }
    # User has elected to edit their playlist details.
    if edit and user.id == request.user.id:
        template = 'isisdata/playlist_edit.html'
        form = UserCitationCollectionForm(initial={
            'name': collection.name,
            'description': collection.description,
            'coverimage_url': collection.coverimage_url,
        })
        
        context.update({'form': form})
    elif form_error:
        context.update({'form': form})
        template = 'isisdata/playlist_edit.html'
    else:
        template = 'isisdata/playlist.html'

    return render(request, template, context)

@login_required()
def create_playlist(request):
    template = 'isisdata/create_playlist.html'
    context = {}

    if request.method == 'POST':
        print('aaaa')
    else:
        form = UserCitationCollectionForm()
        context.update({
            'form': form
        })

    return render(request, template, context)

@login_required()
def add_citation_to_playlist(request):
    if request.method == 'POST':
        playlist_id = request.POST.get('playlist_id')
        citation_id = request.POST.get('citation_id')
        collection = get_object_or_404(CitationCollection, id=playlist_id)
        if request.user.is_authenticated and collection.createdBy == request.user:
            collection.citations.add(Citation.objects.get(id=citation_id))

        context = {
            'collection_name': collection.name,
            'collection_id': collection.id,
            'collection_url': reverse('playlist', kwargs={'collection_id': collection.id})
        }

        return JsonResponse(context)

@login_required()
def remove_citation_from_playlist(request):
    if request.method == 'POST':
        collection_id = request.POST.get('collection_id')
        citation_id = request.POST.get('citation_id')
        collection = get_object_or_404(CitationCollection, id=collection_id)
        citation = get_object_or_404(Citation, pk=citation_id)
        if request.user.is_authenticated and collection.createdBy == request.user:
            collection.citations.remove(citation)

        context = {
            'collection_name': collection.name,
            'collection_id': collection.id,
            'citation_title': citation.title,
            'citation_id': citation.id,
        }

        return JsonResponse(context)

def generate_csv_from_playlist(request, *args, **kwargs):
    collection_id = kwargs.get('collection_id')
    collection = get_object_or_404(CitationCollection, id=collection_id)
    citation_ids = [citation.id for citation in collection.citations.all()]
    citations = Citation.objects.filter(pk__in=citation_ids)

    response = HttpResponse(
        content_type='text/csv',
    )

    response['Content-Disposition'] = 'attachment; filename="{name}_playlist_{playlist_name}.csv"'.format(name=request.user, playlist_name=collection.name)

    writer = csv.writer(response)
    writer.writerow(['Title', 'Authors/Editors', 'Publication Year', 'Type', 'Abstract', 'Publisher', 'Volume', 'Issue/Number', 'Language'])
    for citation in citations:
        authors = citation.acrelation_set.filter(type_controlled__in=[ACRelation.AUTHOR, ACRelation.CONTRIBUTOR, ACRelation.EDITOR], citation__public=True, public=True)
        author_names = ';'.join([author.authority.name if author.authority else author.name_for_display_in_citation for author in authors]) if authors else ''

        publishers = citation.acrelation_set.exclude(type_controlled__in=[ACRelation.AUTHOR, ACRelation.CONTRIBUTOR, ACRelation.EDITOR, ACRelation.SUBJECT, ACRelation.CATEGORY]).filter(type_controlled__in=ACRelation.PERIODICAL).filter(type_controlled__in=ACRelation.PUBLISHER).filter(public=True)
        publisher_names = ';'.join([publisher.authority.name if publisher.authority else publisher.name_for_display_in_citation for publisher in publishers]) if publishers else ''

        volume = citation.part_details.volume if citation.part_details.volume else citation.part_details.volume_free_text if citation.part_details.volume_free_text else ''
        if citation.part_details.issue_begin:
            issue = citation.part_details.issue_begin
            if citation.part_details.issue_end:
                issue += '-' + citation.part_details.issue_end

        languages = ';'.join([language.name for language in citation.language.all()]) if citation.language else ''
        writer.writerow([citation.title, author_names, citation.publication_date.year, citation.get_type_controlled_display(), citation.abstract, publisher_names, volume, issue, languages])

    return response
@ensure_csrf_cookie
def graph_explorer(request):
    context = {}

    if request.method == 'POST':

        node_ids = set()
        nodes = []
        links = []
        subjects = json.loads(request.body)['subjects']

        for subject in subjects:
            node_ids.add(subject) #add the CBA id of the selected subjects to node_ids

            sqs =SearchQuerySet().models(Citation).facet('subject_ids', size=50)

            word_cloud_results = sqs.all().exclude(public="false").filter_or(author_ids=subject).filter_or(contributor_ids=subject) \
                    .filter_or(editor_ids=subject).filter_or(subject_ids=subject).filter_or(institution_ids=subject) \
                    .filter_or(category_ids=subject).filter_or(advisor_ids=subject).filter_or(translator_ids=subject) \
                    .filter_or(publisher_ids=subject).filter_or(school_ids=subject).filter_or(meeting_ids=subject) \
                    .filter_or(periodical_ids=subject).filter_or(book_series_ids=subject).filter_or(time_period_ids=subject) \
                    .filter_or(geographic_ids=subject).filter_or(about_person_ids=subject).filter_or(other_person_ids=subject)

            #add subjects to list of nodes
            subject_ids_facets = word_cloud_results.facet_counts()['fields']['subject_ids'] if 'fields' in word_cloud_results.facet_counts() else []
            for subject_ids_facet in subject_ids_facets:
                node_ids.add(subject_ids_facet[0])
            #remove selected authority from facet results
            subject_ids = [x for x in subject_ids_facets if x[0].upper() != subject.upper()]

            #create links between selected authority and its related subjects
            if subject_ids:
                for subject_id in subject_ids:
                    link = {}
                    link['source'] = subject
                    link['target'] = subject_id[0]
                    link['value'] = subject_id[1]
                    links.append(link)

        authorities = Authority.objects.filter(pk__in=list(node_ids)).values('id', 'name', 'type_controlled')
        if authorities:
            for authority in authorities:
                node = {}
                node['id'] = authority['id']
                node['name'] = authority['name']
                node['type'] = authority['type_controlled']
                node['selected'] = True if authority['id'] in subjects else False
                nodes.append(node)

        context = {
            'nodes': json.dumps(nodes),
            'links': json.dumps(links),
            'subjects': subjects,
        }

        return JsonResponse(context)

    return render(request, 'isisdata/graph_explorer.html', context)

@ensure_csrf_cookie
def term_explorer(request):
    leftSelected = rightSelected = []

    selected = {
        'left': leftSelected,
        'right': rightSelected,
    }

    context = {
        'selected': selected,
    }

    if request.method == 'POST':
        left_ids = json.loads(request.body)['left']
        right_ids = json.loads(request.body)['right']

        left_authorities, left_selected_names = get_authorities(left_ids)
        right_authorities, right_selected_names = get_authorities(right_ids)

        left_boxes = get_facet_boxes(left_authorities)
        right_boxes = get_facet_boxes(right_authorities)

        context['left_selected_ids'] = left_ids
        context['right_selected_ids'] = right_ids
        context['left_selected_names'] = left_selected_names
        context['right_selected_names'] = right_selected_names
        context['left_boxes'] = left_boxes
        context['right_boxes'] = right_boxes

        return JsonResponse(context)

    return render(request, 'isisdata/term_explorer.html', context)

def get_facet_boxes(authorities):
    sqs = SearchQuerySet().models(Citation).facet('all_contributor_ids', size=100). \
                facet('geographic_ids', size=1000).facet('time_period_ids', size=100).\
                facet('publisher_ids', size=100).facet('periodical_ids', size=100).\
                facet('concepts_by_subject_ids', size=100).facet('people_by_subject_ids', size=100).\
                facet('institutions_by_subject_ids', size=100).facet('geocodes', size=1000)

    sqs = sqs.all().exclude(public="false")

    for authority in authorities:
        if authority.type_controlled == authority.CONCEPT:
            sqs = sqs.narrow(u'%s:"%s"' % ('concepts_by_subject_ids_exact', authority.id))
        elif authority.type_controlled == authority.TIME_PERIOD:
            sqs = sqs.narrow(u'%s:"%s"' % ('time_period_ids_exact', authority.id))
        elif authority.type_controlled == authority.GEOGRAPHIC_TERM:
            sqs = sqs.narrow(u'%s:"%s"' % ('geographic_ids_exact', authority.id))
        elif authority.type_controlled == authority.SERIAL_PUBLICATION:
            sqs = sqs.narrow(u'%s:"%s"' % ('periodical_ids', authority.id))
        elif authority.type_controlled == authority.CLASSIFICATION_TERM:
            sqs = sqs.narrow(u'%s:"%s"' % ('category_ids_exact', authority.id))
        elif authority.type_controlled == authority.PERSON:
            if_author_results = sqs.narrow(u'%s:"%s"' % ('persons_ids', authority.id))
            if_person_results = sqs.narrow(u'%s:"%s"' % ('people_by_subject_ids', authority.id))
            if if_author_results.count() >= if_person_results.count():
                sqs = if_author_results
            else:
                sqs = if_person_results
        elif authority.type_controlled == authority.INSTITUTION:
            if_publisher_results = sqs.narrow(u'%s:"%s"' % ('publisher_ids', authority.id))
            if_institution_results = sqs.narrow(u'%s:"%s"' % ('institutions_by_subject_ids_exact', authority.id))
            if if_publisher_results.count() >= if_institution_results.count():
                sqs = if_publisher_results
            else:
                sqs = if_institution_results

    total_citations = sqs.count()

    facet_types = ['all_contributor_ids', 'periodical_ids', 'publisher_ids', 'people_by_subject_ids', 'geographic_ids', 'concepts_by_subject_ids', 'time_period_ids', 'institutions_by_subject_ids']
    facet_name_map = {
        'all_contributor_ids': 'contributors',
        'periodical_ids': 'journals',
        'publisher_ids': 'publishers',
        'people_by_subject_ids': 'people',
        'geographic_ids': 'places',
        'concepts_by_subject_ids': 'concepts',
        'time_period_ids': 'times',
        'institutions_by_subject_ids': 'institutions',
    }

    facets = {}

    for facet_type in facet_types:
        facet = sqs.facet_counts()['fields'][facet_type] if 'fields' in sqs.facet_counts() else []
        # remove current authority from facet results
        facet = remove_self_from_facets(facet, [authority.id for authority in authorities])
        # assign ranks to each authority
        facet = rank(facet)
        # get authority name for facet results
        facet = get_facets_authority_name(facet, total_citations)

        facets[facet_name_map[facet_type]] = facet

    return facets

def rank(facets):
    # This method arranges facet box items by related citation count in descending
    # order and assigns a rank to each facet. Facets with the same count are assinged
    # the same rank even though they'll have a different index value in the list.
    new_facets = []
    prev = None
    place = 0
    for i,(id, count) in enumerate(facets):
        if count != prev:
            place = place + 1
            prev = count
        new_facet = (id, count, place)
        new_facets.append(new_facet)

    return new_facets

def get_authorities(authority_ids):
    authorities = Authority.objects.filter(id__in=authority_ids)
    names = [authority.name for authority in authorities]
    return authorities, names

def get_facets_authority_name(facets, total_citations):
    new_facets = []
    for facet in facets:
        authority_object = Authority.objects.get(id=facet[0])
        name = authority_object.name
        new_facet = {}
        new_facet['name'] = name
        new_facet['count'] = facet[1]
        new_facet['id'] = facet[0]
        new_facet['rank'] = facet[2]
        new_facet['percent'] = round(facet[1]/total_citations * 100, 2)
        new_facets.append(new_facet)
    return new_facets

def remove_self_from_facets(facet, authority_ids):
    return [x for x in facet if x[0].upper() not in authority_ids]

@ensure_csrf_cookie
def ngram_explorer(request):

    context = {
    }

    if request.method == 'POST':
        context = {}
        selected_groups = json.loads(request.body)
        data = []
        max_years = []
        min_years = []
        max_ngrams = []

        for selected_group in selected_groups:
            if selected_groups[selected_group]:
                group = {}
                authorities, names = get_authorities(selected_groups[selected_group])
                group['name'] = selected_group
                group['selected_ids'] = selected_groups[selected_group]
                group['authority_names'] = names
                group['values'], group_max_year, group_min_year, group_max_ngram = get_ngram_data(selected_groups[selected_group])
                data.append(group)
                max_years.append(group_max_year)
                min_years.append(group_min_year)
                max_ngrams.append(group_max_ngram)

        context['max_year'] = max(max_years)
        context['min_year'] = min(min_years)
        context['max_ngram'] = max(max_ngrams)
        context['data'] = data

        return JsonResponse(context)

    return render(request, 'isisdata/ngram_explorer.html', context)

def get_ngram_data(authority_ids):
    sqs_all =SearchQuerySet().models(Citation).auto_query('*').facet('publication_date')
    all_facet_results = sqs_all.all().exclude(public="false")
    all_pub_date_facet = all_facet_results.facet_counts()['fields']['publication_date'] if 'fields' in all_facet_results.facet_counts() else []
    all_pub_date_facet = clean_dates(all_pub_date_facet)
    all_dates_map = {}
    citations = 0
    for facet in all_pub_date_facet:
        all_dates_map[facet[0]] = facet[1]
        citations = citations + facet[1]

    sqs =SearchQuerySet().models(Citation).facet('publication_date', size=200)

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


def clean_dates(date_facet):
    new_date_facet = []
    for date in date_facet:
        date_pattern = re.compile("^[0-9]{4}$")
        if re.search(date_pattern, date[0]) and int(date[0]) >= 1965:
            new_date_facet.append(date)
    return new_date_facet

def quick_create_aprelation(request):
    if request.method == 'POST':
        authority_id = request.POST.get('authority_id')
        playlist_id = request.POST.get('playlist_id')
        playlist = CitationCollection.objects.get(pk=playlist_id)
        authority = Authority.objects.get(pk=authority_id)
        playlist.subjects.add(authority)

        response_data = {
            'authority': {
                'id': authority.id,
                'name': authority.name,
            },
        }
        return JsonResponse(response_data)

def quick_delete_aprelation(request):
    if request.method == 'POST':
        authority_id = request.POST.get('authority_id')
        playlist_id = request.POST.get('playlist_id')
        playlist = CitationCollection.objects.get(pk=playlist_id)
        authority = Authority.objects.get(pk=authority_id)
        playlist.subjects.remove(authority)

        response_data = {
            'authority': {
                'id': authority.id,
            },
        }
        return JsonResponse(response_data)

    
