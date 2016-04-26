from django import forms
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger, InvalidPage
from django.core.cache import caches
from django.core.cache.backends.base import InvalidCacheBackendError
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden, Http404, HttpResponseRedirect, JsonResponse
from django.views.generic.edit import FormView
from django.template import RequestContext, loader

import uuid
import base64, zlib

from haystack.generic_views import FacetedSearchView
from haystack.query import EmptySearchQuerySet

from rest_framework import viewsets, serializers, mixins, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

import rest_framework_filters as filters

from oauth2_provider.ext.rest_framework import TokenHasScope, OAuth2Authentication

from urllib import quote, urlopen
import codecs
from collections import defaultdict
from helpers.mods_xml import initial_response, generate_mods_xml
from helpers.linked_data import generate_authority_rdf, generate_citation_rdf
import datetime
from ipware.ip import get_real_ip
import xml.etree.ElementTree as ET

from isisdata.models import *
from isisdata.forms import UserRegistrationForm, UserProfileForm
from isisdata.templatetags.metadata_filters import get_coins_from_citation
from isisdata import helper_methods


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

    class Meta:
        model = Value
        fields = ('value', 'value_type')


class ContentTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ContentType
        fields = ('url', 'model')


class AttributeTypeSerializer(serializers.HyperlinkedModelSerializer):
    content_type = ContentTypeSerializer(source='value_content_type')

    class Meta:
        model = AttributeType
        fields = ('url', 'id', 'name', 'content_type')


class AttributeSerializer(serializers.HyperlinkedModelSerializer):
    type_controlled = AttributeTypeSerializer(many=False)
    source = GenericHyperlink(many=False, read_only=True)
    value = ValueSerializer(many=False, read_only=True)

    class Meta:
        model = Attribute
        fields = ('uri', 'url', 'id',
                  'type_controlled',
                  'type_controlled_broad',
                  'source',
                  'value',
                  'value_freeform')


class LanguageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Language
        fields = ('url', 'id', 'name')


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'id', 'username', 'date_joined')


class ContentTypeRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        return value.id

    def to_internal_value(self, data):

        return ContentType.objects.get(pk=data)

class UserRelatedSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
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

    class Meta:
        model = Comment

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
    class Meta:
        model = LinkedDataType


class LinkedDataSerializer(serializers.HyperlinkedModelSerializer):
    type_controlled = LinkedDataTypeSerializer(many=False)
    class Meta:
        model = LinkedData
        fields = ('universal_resource_name', 'description', 'type_controlled')


class CCRelationSerializer(serializers.HyperlinkedModelSerializer):
    attributes = AttributeSerializer(many=True, read_only=True)
    linked_data = LinkedDataSerializer(many=True, read_only=True,
                                       source='linkeddata_entries')

    class Meta:
        model = CCRelation

        fields = ('uri', 'url', 'id',
                  'subject', 'object',
                  'name',
                  'description',
                  'type_controlled',
                  'attributes',
                  'linked_data')

class CCRelationSparseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CCRelation

        fields = ('uri', 'url', 'id',
                  'subject', 'object',
                  'name',
                  'type_controlled')


class ACRelationSerializer(serializers.HyperlinkedModelSerializer):
    attributes = AttributeSerializer(many=True, read_only=True)
    linked_data = LinkedDataSerializer(many=True, read_only=True,
                                       source='linkeddata_entries')

    class Meta:
        model = ACRelation

        fields = ('uri', 'url', 'id',
                  'citation', 'authority',
                  'name',
                  'description',
                  'type_controlled',
                  'attributes',
                  'linked_data')


class ACRelationSparseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ACRelation

        fields = ('uri', 'url', 'id',
                  'citation', 'authority',
                  'name',
                  'type_controlled')


class AARelationSerializer(serializers.HyperlinkedModelSerializer):
    attributes = AttributeSerializer(many=True, read_only=True)
    linked_data = LinkedDataSerializer(many=True, read_only=True,
                                       source='linkeddata_entries')

    class Meta:
        model = AARelation

        fields = ('uri', 'url', 'id',
                  'subject', 'object',
                  'name',
                  'description',
                  'type_controlled',
                  'attributes',
                  'linked_data')


class AARelationSparseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = AARelation

        fields = ('uri', 'url', 'id',
                  'subject', 'object',
                  'name',
                  'type_controlled')


class AuthoritySerializer(serializers.HyperlinkedModelSerializer):
    attributes = AttributeSerializer(many=True, read_only=True)
    linked_data = LinkedDataSerializer(many=True, read_only=True,
                                       source='linkeddata_entries')
    related_citations = ACRelationSparseSerializer(read_only=True, many=True,
                                                   source='acrelations')
    related_authorities = AARelationSparseSerializer(read_only=True, many=True,
                                                     source='aarelations')

    class Meta:
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

    class Meta:
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
    class Meta:
        model = PartDetails


class AuthorityFilterSet(filters.FilterSet):
    name = filters.AllLookupsFilter(name='name')
    class Meta:
        model = Authority
        fields = ['name', 'type_controlled']


class AuthorityViewSet(mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       viewsets.GenericViewSet):
    queryset = Authority.objects.all()
    serializer_class = AuthoritySerializer
    filter_class = AuthorityFilterSet
    filter_fields = ('name', )


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
    template = loader.get_template('isisdata/index.html')
    context = RequestContext(request, {
        'test': False,
    })
    return HttpResponse(template.render(context))

def index(request, obj_id=None):
    template = loader.get_template('isisdata/index.html')
    if (obj_id == None):
        context = RequestContext(request, {

        })
        return HttpResponse(template.render(context))
    try:
        object = Authority.objects.get(id=obj_id)
    except Authority.DoesNotExist:
        object = None
    if object != None:
        return redirect('authority', authority_id = obj_id)

    return redirect('citation', citation_id = obj_id)

    #context = RequestContext(request, {
    #    'test': False,
    #})
    #return HttpResponse(template.render(context))


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
    template = loader.get_template('isisdata/help.html')

    context = RequestContext(request, {
        'active': 'help',
    })
    return HttpResponse(template.render(context))

def about(request):
    """
    View for about page
    """
    template = loader.get_template('isisdata/about.html')

    context = RequestContext(request, {
        'active': 'about',
    })
    return HttpResponse(template.render(context))

def authority(request, authority_id):
    """
    View for individual Authority entries.
    """

    authority = Authority.objects.get(id=authority_id)

    if not authority.public:
        return HttpResponseForbidden()

    # Some authority entries are deleted. These should be hidden from public
    #  view.
    if authority.record_status == 'DL':
        return Http404("No such Authority")

    # If the user has been redirected from another Authority entry, this should
    #  be indicated in the view.
    redirect_from_id = request.GET.get('redirect_from')
    if redirect_from_id:
        redirect_from = Authority.objects.get(pk=redirect_from_id)
    else:
        redirect_from = None

    # There are several authority entries that redirect to other entries,
    #  usually because the former is a duplicate of the latter.
    if authority.record_status == 'RD' and authority.redirect_to is not None:
        redirect_kwargs = {'authority_id': authority.redirect_to.id}
        base_url = reverse('authority', kwargs=redirect_kwargs)
        redirect_url = base_url + '?redirect_from={0}'.format(authority.id)
        return HttpResponseRedirect(redirect_url)

    template = loader.get_template('isisdata/authority.html')

    show_nr = 3
    related_citations_author = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['AU'], citation__public=True).order_by('-citation__publication_date')[:show_nr]
    related_citations_author_count = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['AU']).distinct('citation_id').count()

    related_citations_editor = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['ED'], citation__public=True).order_by('-citation__publication_date')[:show_nr]
    related_citations_editor_count = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['ED'], citation__public=True).distinct('citation_id').count()

    related_citations_advisor = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['AD'], citation__public=True).order_by('-citation__publication_date')[:show_nr]
    related_citations_advisor_count = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['AD'], citation__public=True).distinct('citation_id').count()

    related_citations_contributor = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['CO'], citation__public=True).order_by('-citation__publication_date')[:show_nr]
    related_citations_contributor_count = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['CO'], citation__public=True).distinct('citation_id').count()

    related_citations_translator = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['TR'], citation__public=True).order_by('-citation__publication_date')[:show_nr]
    related_citations_translator_count = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['TR'], citation__public=True).distinct('citation_id').count()

    related_citations_subject = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['SU'], citation__public=True).order_by('-citation__publication_date')[:show_nr]
    related_citations_subject_count = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['SU'], citation__public=True).distinct('citation_id').count()

    related_citations_category = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['CA'], citation__public=True).order_by('-citation__publication_date')[:show_nr]
    related_citations_category_count = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['CA'], citation__public=True).distinct('citation_id').count()

    related_citations_publisher = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['PU'], citation__public=True).order_by('-citation__publication_date')[:show_nr]
    related_citations_publisher_count = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['PU'], citation__public=True).distinct('citation_id').count()

    related_citations_school = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['SC'], citation__public=True).order_by('-citation__publication_date')[:show_nr]
    related_citations_school_count = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['SC'], citation__public=True).distinct('citation_id').count()

    related_citations_institution = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['IN'], citation__public=True).order_by('-citation__publication_date')[:show_nr]
    related_citations_institution_count = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['IN'], citation__public=True).distinct('citation_id').count()

    related_citations_meeting = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['ME'], citation__public=True).order_by('-citation__publication_date')[:show_nr]
    related_citations_meeting_count = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['ME'], citation__public=True).distinct('citation_id').count()

    related_citations_periodical = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['PE'], citation__public=True).order_by('-citation__publication_date')[:show_nr]
    related_citations_periodical_count = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['PE'], citation__public=True).distinct('citation_id').count()

    related_citations_book_series = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['BS'], citation__public=True).order_by('-citation__publication_date')[:show_nr]
    related_citations_book_series_count = ACRelation.objects.filter(authority=authority,
                                                  type_controlled__in=['BS'], citation__public=True).distinct('citation_id').count()

    # Location of authority in REST API
    api_view = reverse('authority-detail', args=[authority.id], request=request)

    # Provide progression through search results, if present.
    last_query = request.GET.get('last_query', None) #request.session.get('last_query', None)
    query_string = request.GET.get('query_string', None)
    fromsearch = request.GET.get('fromsearch', False)
    if query_string:
        query_string = query_string.encode('ascii','ignore')
        search_key = base64.b64encode(query_string) #request.session.get('search_key', None)
    else:
        search_key = None

    # This is the database cache.
    user_cache = caches['default']
    search_results = user_cache.get('search_results_authority_' + str(search_key))

    # make sure we have a session key
    if hasattr(request, 'session') and not request.session.session_key:
        request.session.save()
        request.session.modified = True

    session_id = request.session.session_key
    page_authority = user_cache.get(session_id + '_page_authority', None)

    if search_results and fromsearch and page_authority:
        search_count = search_results.count()
        prev_search_result = None
        if (page_authority > 1):
            prev_search_result = search_results[(page_authority - 1)*20 - 1]

        # if we got to the last result of the previous page we need to count down the page number
        if prev_search_result == 'isisdata.authority.' + authority_id:
            page_authority = page_authority - 1
            user_cache.set(session_id + '_page_authority', page_authority)

        search_results_page = search_results[(page_authority - 1)*20:page_authority*20 + 2]

        try:
            search_index = search_results_page.index('isisdata.authority.' + authority_id) + 1   # +1 for display.
            if search_index == 21:
                user_cache.set(session_id + '_page_authority', page_authority+1)

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

        # !! Why are we catching all of these errors?
        except (IndexError, ValueError, AssertionError, TypeError):
            search_previous = None
        if search_index:
            search_current = search_index + (20* (page_authority - 1))
        else:
            search_current = None
    else:
        search_index = None
        search_next = None
        search_previous = None
        search_current = None
        search_count = None


    context = RequestContext(request, {
        'authority_id': authority_id,
        'authority': authority,
        'related_citations_author': related_citations_author,
        'related_citations_author_count': related_citations_author_count,
        'related_citations_editor': related_citations_editor,
        'related_citations_editor_count': related_citations_editor_count,
        'related_citations_advisor': related_citations_advisor,
        'related_citations_advisor_count': related_citations_advisor_count,
        'related_citations_contributor': related_citations_contributor,
        'related_citations_contributor_count': related_citations_contributor_count,
        'related_citations_translator': related_citations_translator,
        'related_citations_translator_count': related_citations_translator_count,
        'related_citations_subject': related_citations_subject,
        'related_citations_subject_count': related_citations_subject_count,
        'related_citations_category': related_citations_category,
        'related_citations_category_count': related_citations_category_count,
        'related_citations_publisher': related_citations_publisher,
        'related_citations_publisher_count': related_citations_publisher_count,
        'related_citations_school': related_citations_school,
        'related_citations_school_count': related_citations_school_count,
        'related_citations_institution': related_citations_institution,
        'related_citations_institution_count': related_citations_institution_count,
        'related_citations_meeting': related_citations_meeting,
        'related_citations_meeting_count': related_citations_meeting_count,
        'related_citations_periodical': related_citations_periodical,
        'related_citations_periodical_count': related_citations_periodical_count,
        'related_citations_book_series': related_citations_book_series,
        'related_citations_book_series_count': related_citations_book_series_count,
        'source_instance_id': authority_id,
        'source_content_type': ContentType.objects.get(model='authority').id,
        'api_view': api_view,
        'redirect_from': redirect_from,
        'search_results': search_results,
        'search_index': search_index,
        'search_next': search_next,
        'search_previous': search_previous,
        'search_current': search_current,
        'search_count': search_count,
        'fromsearch': fromsearch,
        'last_query': last_query,
        'query_string': query_string,
    })
    return HttpResponse(template.render(context))


def citation(request, citation_id):
    """
    View for individual citation record.
    """
    template = loader.get_template('isisdata/citation.html')
    citation = get_object_or_404(Citation, pk=citation_id)

    if not citation.public:
        return HttpResponseForbidden()

    # Some citations are deleted. These should be hidden from public view.
    if citation.status_of_record == 'DL':
        return Http404("No such Citation")

    authors = citation.acrelation_set.filter(type_controlled__in=['AU', 'CO', 'ED'], citation__public=True)

    subjects = citation.acrelation_set.filter(Q(type_controlled__in=['SU'], citation__public=True) & ~Q(authority__type_controlled__in=['GE', 'TI'], citation__public=True))
    persons = citation.acrelation_set.filter(type_broad_controlled__in=['PR'], citation__public=True)
    categories = citation.acrelation_set.filter(Q(type_controlled__in=['CA']), citation__public=True)

    query_time = Q(type_controlled__in=['TI'], citation__public=True) | (Q(type_controlled__in=['SU'], citation__public=True) & Q(authority__type_controlled__in=['TI'], citation__public=True))
    time_periods = citation.acrelation_set.filter(query_time)

    query_places = Q(type_controlled__in=['SU'], citation__public=True) & Q(authority__type_controlled__in=['GE'], citation__public=True)
    places = citation.acrelation_set.filter(query_places)

    related_citations_ic = CCRelation.objects.filter(subject_id=citation_id, type_controlled='IC', object__public=True)
    related_citations_inv_ic = CCRelation.objects.filter(object_id=citation_id, type_controlled='IC', subject__public=True)
    related_citations_isa = CCRelation.objects.filter(subject_id=citation_id, type_controlled='ISA', object__public=True)
    related_citations_inv_isa = CCRelation.objects.filter(object_id=citation_id, type_controlled='ISA', subject__public=True)

    query = Q(subject_id=citation_id, type_controlled='RO', object__public=True) | Q(object_id=citation_id, type_controlled='RB', subject__public=True)
    related_citations_ro = CCRelation.objects.filter(query)

    related_citations_rb = CCRelation.objects.filter(subject_id=citation_id, type_controlled='RB', object__public=True)
    related_citations_re = CCRelation.objects.filter(subject_id=citation_id, type_controlled='RE', object__public=True)
    related_citations_inv_re = CCRelation.objects.filter(object_id=citation_id, type_controlled='RE', subject__public=True)
    related_citations_as = CCRelation.objects.filter(subject_id=citation_id, type_controlled='AS', object__public=True)

    properties = citation.acrelation_set.exclude(type_controlled__in=['AU', 'ED', 'CO', 'SU', 'CA'])
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
        query_string = query_string.encode('ascii','ignore')
        search_key = base64.b64encode(last_query)
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

    context = RequestContext(request, {
        'citation_id': citation_id,
        'citation': citation,
        'authors': authors,
        'properties_map': properties,
        'subjects': subjects,
        'persons': persons,
        'categories': categories,
        'time_periods': time_periods,
        'places': places,
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
    })
    return HttpResponse(template.render(context))


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


    template = loader.get_template('isisdata/search_saved.html')
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

    context = RequestContext(request, {
        'searchqueries': searchqueries,
    })
    return HttpResponse(template.render(context))



@login_required
def search_history(request):
    """
    Provides the search history for a logged-in user.
    """

    # If the user is Anonymous, redirect them to the login view.
    if not type(request.user._wrapped) is User:
        return HttpResponseRedirect(reverse('login'))

    template = loader.get_template('isisdata/search_history.html')
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

    context = RequestContext(request, {
        'searchqueries': searchqueries,
    })
    return HttpResponse(template.render(context))


class IsisSearchView(FacetedSearchView):
    """
    Provides the search view at /isis/
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
        if parameters:
            parameters = parameters.encode('ascii', 'ignore')
        search_models = self.request.GET.get('models', None)
        selected_facets = self.request.GET.get('selected_facets', None)

        sort_field_citation = self.request.GET.get('sort_order_citation', None)
        sort_order_citation = self.request.GET.get('sort_order_dir_citation', None)
        sort_field_authority = self.request.GET.get('sort_order_authority', None)
        sort_order_authority = self.request.GET.get('sort_order_dir_authority', None)

        # If the user is logged in, attempt to save the search in their
        #  search history.
        if log and parameters and self.request.user.id > 0:
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
        cache_key = u'{0}_{1}_{2}_{3}_{4}_{5}_{6}'.format(parameters, search_models, selected_facets, sort_field_citation, sort_order_citation, sort_field_authority, sort_order_authority)

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
        User.objects.create_user(cleaned_data['username'],
                                 cleaned_data['email'],
                                 cleaned_data['password1'])

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

    template = loader.get_template('isisdata/home.html')

    context = RequestContext(request, {
        'active': 'home',
        'comments_citation': Comment.objects.filter(subject_content_type__model='citation').order_by('-modified_on')[:10],
        'comments_authority': Comment.objects.filter(subject_content_type__model='authority').order_by('-modified_on')[:10]
    })

    return HttpResponse(template.render(context))

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

    template = loader.get_template('isisdata/api.html')
    rest_endpoint = request.build_absolute_uri(reverse('rest_root'))
    context = RequestContext(request, {
        'active': 'about',
        'rest_endpoint': rest_endpoint,
    })
    return HttpResponse(template.render(context))


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
        linkIcon = resolver.find(worldcat_tag + 'linkIcon').text.strip()
        linkText = resolver.find(worldcat_tag + 'linkText').text.strip()
        return {
            'url': url,
            'icon': linkIcon,
            'text': linkText,
        }
    return


def get_linkresolver_url(request, citation_id):
    citation = get_object_or_404(Citation, pk=citation_id)
    data = None
    if request.user.id > 0:
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
    edit = request.GET.get('edit')

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
    context = RequestContext(request, {
        'active': '',
        'username': user.username,
        'full_name': '%s %s' % (user.first_name, user.last_name),
        'is_staff': user.is_staff,
        'email': user.email,
        'profile': user.profile,
        'usercomments': comments,
    })

    # User has elected to edit their own profile.
    if edit and user.id == request.user.id:
        # This template has an almost identical layout to userprofile.html,
        #  except that display fields are replaced with input fields.
        template = loader.get_template('isisdata/userprofile_edit.html')
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
        template = loader.get_template('isisdata/userprofile_edit.html')
    else:
        template = loader.get_template('isisdata/userprofile.html')
    return HttpResponse(template.render(context))
