from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger, InvalidPage
from django.core.cache import cache
from django.core.cache.backends.base import InvalidCacheBackendError
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django import forms
from django.db import connection
from django.http import HttpResponse, HttpResponseForbidden, Http404
from django.db.models import Q

import uuid

# Used by UserRegistrationView and UserRegistrationForm
from registration.forms import RegistrationForm
from captcha.fields import CaptchaField
from registration.views import RegistrationView

from haystack.views import FacetedSearchView
from haystack.query import EmptySearchQuerySet

from rest_framework import viewsets, serializers, mixins, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from oauth2_provider.ext.rest_framework import TokenHasScope, OAuth2Authentication

from isisdata.models import *


from django.template import RequestContext, loader
from django.http import HttpResponse, HttpResponseRedirect
from urllib import quote
import codecs

from collections import defaultdict

from helpers.mods_xml import initial_response, generate_mods_xml

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

# class ValueHyperlink(serializers.HyperlinkedRelatedField):
#     view_name = 'value-detail'
#
#     def get_url(self, obj, v, request, format):
#         view_name = obj.child_class.lower() + '-detail'
#         print view_name
#         return super(ValueHyperlink, self).get_url(obj, view_name,
#                                                    request, format)


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
        fields = ('uri', 'url', 'name',
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


class AuthorityViewSet(mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       viewsets.GenericViewSet):
    queryset = Authority.objects.all()
    serializer_class = AuthoritySerializer


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
    fromsearch = request.GET.get('fromsearch', False)
    search_key = request.session.get('search_key', None)
    search_results = cache.get('search_results_authority_' + str(search_key))

    page_authority = request.session.get('page_authority', None)

    if search_results and fromsearch and page_authority:
        search_count = search_results.count()
        search_results_page = search_results[(page_authority - 1)*20:page_authority*20]

        try:
            search_index = search_results_page.index('isisdata.authority.' + authority_id) + 1   # +1 for display.
        except IndexError:
            search_index = None
        try:
            search_next = search_results_page[search_index]
        except IndexError:
            search_next = None
        try:
            search_previous = search_results_page[search_index - 2]
        except IndexError:
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


    last_query = request.session.get('last_query', None)

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
    fromsearch = request.GET.get('fromsearch', False)
    search_key = request.session.get('search_key', None)
    search_results = cache.get('search_results_citation_' + str(search_key))
    page_citation = request.session.get('page_citation', None)

    if search_results and fromsearch and page_citation:
        search_count = search_results.count()
        search_results_page = search_results[(page_citation - 1)*20:page_citation*20]

        try:
            search_index = search_results_page.index('isisdata.citation.' + citation_id) + 1   # +1 for display.
        except IndexError:
            search_index = None
        try:
            search_next = search_results_page[search_index]
        except IndexError:
            search_next = None
        try:
            search_previous = search_results_page[search_index - 2]
        except IndexError:
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

    last_query = request.session.get('last_query', None)

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
    def __call__(self, request):
        """
        Overridden to provide search history log functionality.
        """

        page_citation = request.GET.get('page_citation', 1)
        page_authority = request.GET.get('page_authority', 1)

        s = datetime.datetime.now()
        self.request = request
        print 'request', datetime.datetime.now() - s

        s = datetime.datetime.now()
        self.form = self.build_form()
        print 'form', datetime.datetime.now() - s

        s = datetime.datetime.now()
        self.query = self.get_query()
        print 'query', datetime.datetime.now() - s

        # If the user is logged in, record the search in their history.
        s = datetime.datetime.now()
        log = request.GET.get('log', 'True') != 'False'
        parameters = request.GET.get('q', None)
        search_models = request.GET.get('models', None)
        selected_facets = request.GET.get('selected_facets', None)
        if log and parameters and request.user.id > 0:
            searchquery = SearchQuery(
                user = request.user._wrapped,
                parameters = parameters,
                search_models = search_models,
                selected_facets = selected_facets,
            )
            searchquery.save()
            request.session['last_query'] = request.get_full_path()
        print 'history', datetime.datetime.now() - s
        cache_key = u'{0}_{1}_{2}'.format(parameters, search_models, selected_facets)

        s = datetime.datetime.now()
        self.results = cache.get(cache_key)
        print 'getcache', datetime.datetime.now() - s
        if not self.results:
            s = datetime.datetime.now()
            self.results = self.get_results()
            print 'get_results', datetime.datetime.now() - s

            s = datetime.datetime.now()
            cache.set(cache_key, self.results, 6000)
            print 'set_cache', datetime.datetime.now() - s

        if parameters:  # Store results in the session cache.
            s = datetime.datetime.now()
            search_key = str(uuid.uuid4())
            request.session['search_key'] =  search_key
            request.session['page_citation'] = int(page_citation)
            request.session['page_authority'] = int(page_authority)
            cache.set('search_results_authority_' + str(search_key), self.results['authority'].values_list('id', flat=True))
            cache.set('search_results_citation_' + str(search_key), self.results['citation'].values_list('id', flat=True))

            print 'session cache', datetime.datetime.now() - s

        return self.create_response()

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

        if isinstance(self.results, EmptySearchQuerySet):
            self.results[0:self.results_per_page]
            paginator_authority = Paginator(self.results, self.results_per_page)
            paginator_citation = Paginator(self.results, self.results_per_page)

        else:
            self.results['citation'][start_offset_citation:start_offset_citation + self.results_per_page]
            self.results['authority'][start_offset_authority:start_offset_authority+ self.results_per_page]

            paginator_authority = Paginator(self.results['authority'], self.results_per_page)
            paginator_citation = Paginator(self.results['citation'], self.results_per_page)


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

    def extra_context(self):
        extra = super(FacetedSearchView, self).extra_context()
        extra['request'] = self.request
        if isinstance(self.results, EmptySearchQuerySet):
            extra['facets_citation'] = 0
            extra['facets_authority'] = 0
            extra['count_citation'] = len(self.results)
            extra['count_authority'] = len(self.results)
        else:
            extra['facets_authority'] = self.results['authority'].facet_counts()
            extra['facets_citation'] = self.results['citation'].facet_counts()
            extra['count_citation'] = len(self.results['citation'])
            extra['count_authority'] = len(self.results['authority'])

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


class UserRegistrationForm(RegistrationForm):
    captcha = CaptchaField()
    next = forms.CharField(widget=forms.HiddenInput())


class UserRegistrationView(RegistrationView):
    form_class = UserRegistrationForm

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
        'comments': reversed(Comment.objects.order_by('created_on')[:10])
    })

    return HttpResponse(template.render(context))
