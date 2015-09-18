from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger, InvalidPage

from django.contrib.auth.models import User
from django.db import connection
from django.http import HttpResponse
from django.http import Http404
from django.db.models import Q

from haystack.views import FacetedSearchView

from rest_framework import viewsets, serializers, mixins, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from isisdata.models import *

from django.template import RequestContext, loader
from django.http import HttpResponse
from urllib import quote
import codecs

from collections import defaultdict


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

    class Meta:
        model = Comment

    def create(self, *args, **kwargs):
        """
        Create a new ``Comment`` instance.
        """

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


class CitationViewSet(mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      viewsets.GenericViewSet):
    queryset = Citation.objects.all()
    serializer_class = CitationSerializer


class ACRelationViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    queryset = ACRelation.objects.all()
    serializer_class = ACRelationSerializer


class CCRelationViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    queryset = CCRelation.objects.all()
    serializer_class = CCRelationSerializer


class AARelationViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    queryset = AARelation.objects.all()
    serializer_class = AARelationSerializer


class AttributeTypeViewSet(mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           viewsets.GenericViewSet):
    queryset = AttributeType.objects.all()
    serializer_class = AttributeTypeSerializer
    pagination_class = None     # Angular has trouble with pagination.


class ContentTypeViewSet(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         viewsets.GenericViewSet):
    queryset = ContentType.objects.all()
    serializer_class = ContentTypeSerializer


class ValueViewSet(mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   viewsets.GenericViewSet):
    queryset = Value.objects.all()
    serializer_class = ValueSerializer


class LanguageViewSet(mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      viewsets.GenericViewSet):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer


class AttributeViewSet(mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       viewsets.GenericViewSet):

    queryset = Attribute.objects.all()
    serializer_class = AttributeSerializer


class LinkedDataViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    queryset = LinkedData.objects.all()
    serializer_class = LinkedDataSerializer


class LinkedDataTypeViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    queryset = LinkedDataType.objects.all()
    serializer_class = LinkedDataTypeSerializer


class PartDetailsViewSet(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         viewsets.GenericViewSet):
    queryset = PartDetails.objects.all()
    serializer_class = PartDetailsSerializer


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    pagination_class = None     # Angular has trouble with pagination.

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

def authority(request, authority_id):
    template = loader.get_template('isisdata/authority.html')
    authority = Authority.objects.get(id=authority_id)
    citations_by_list = ACRelation.objects.filter(authority=authority,type_broad_controlled='PR')
    citations_about_list = ACRelation.objects.filter(authority=authority,type_broad_controlled='SC')
    citations_other_list = ACRelation.objects.filter(authority=authority,type_broad_controlled__in=['IH', 'PH'])

    citations_by_paginator = Paginator(citations_by_list, 30)
    citations_about_paginator = Paginator(citations_about_list, 30)
    citations_other_paginator = Paginator(citations_other_list, 30)

    page = request.GET.get('page-about')
    try:
        citations_about = citations_about_paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        citations_about = citations_about_paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        citations_about = citations_about_paginator.page(paginator.num_pages)

    page_other = request.GET.get('page-other')
    try:
        citations_other = citations_other_paginator.page(page_other)
    except PageNotAnInteger:
        citations_other = citations_other_paginator.page(1)
    except EmptyPage:
        citations_other = citations_other_paginator.page(paginator.num_pages)

    page_by = request.GET.get('page-by')
    try:
        citations_by = citations_by_paginator.page(page_by)
    except PageNotAnInteger:
        citations_by = citations_by_paginator.page(1)
    except EmptyPage:
        citations_by = citations_by_paginator.page(paginator.num_pages)

    context = RequestContext(request, {
        'authority_id': authority_id,
        'authority': authority,
        'citations_by': citations_by,
        'citations_about': citations_about,
        'citations_other': citations_other,
        'source_instance_id': authority_id,
        'source_content_type': ContentType.objects.get(model='authority').id,
    })
    return HttpResponse(template.render(context))

def citation(request, citation_id):
    template = loader.get_template('isisdata/citation.html')
    citation = get_object_or_404(Citation, pk=citation_id)
    authors = citation.acrelation_set.filter(type_controlled__in=['AU', 'CO'])
    subjects = citation.acrelation_set.filter(type_controlled__in=['SU'])
    persons = citation.acrelation_set.filter(type_broad_controlled__in=['PR'])
    categories = citation.acrelation_set.filter(type_controlled__in=['CA'])
    time_periods = citation.acrelation_set.filter(type_controlled__in=['TI'])

    related_citations_ic = CCRelation.objects.filter(subject_id=citation_id, type_controlled='IC')
    related_citations_inv_ic = CCRelation.objects.filter(object_id=citation_id, type_controlled='IC')
    related_citations_isa = CCRelation.objects.filter(subject_id=citation_id, type_controlled='ISA')
    related_citations_inv_isa = CCRelation.objects.filter(object_id=citation_id, type_controlled='ISA')
    related_citations_ro = CCRelation.objects.filter(subject_id=citation_id, type_controlled='RO')
    related_citations_rb = CCRelation.objects.filter(subject_id=citation_id, type_controlled='RB')
    related_citations_inv_rb = CCRelation.objects.filter(object_id=citation_id, type_controlled='RB')
    related_citations_re = CCRelation.objects.filter(subject_id=citation_id, type_controlled='RE')
    related_citations_inv_re = CCRelation.objects.filter(object_id=citation_id, type_controlled='RE')
    related_citations_as = CCRelation.objects.filter(subject_id=citation_id, type_controlled='AS')

    properties = citation.acrelation_set.exclude(type_controlled__in=['AU', 'CO', 'SU', 'CA'])
    properties_map = defaultdict(list)
    for prop in properties:
        properties_map[prop.type_controlled] += [prop]

    context = RequestContext(request, {
        'citation_id': citation_id,
        'citation': citation,
        'authors': authors,
        'properties_map': properties,
        'subjects': subjects,
        'persons': persons,
        'categories': categories,
        'time_periods': time_periods,
        'source_instance_id': citation_id,
        'source_content_type': ContentType.objects.get(model='citation').id,
        'related_citations_ic': related_citations_ic,
        'related_citations_inv_ic': related_citations_inv_ic,
        'related_citations_rb': related_citations_rb,
        'related_citations_inv_rb': related_citations_inv_rb,
        'related_citations_isa': related_citations_isa,
        'related_citations_inv_isa': related_citations_inv_isa,
        'related_citations_ro': related_citations_ro,
        'related_citations_re': related_citations_re,
        'related_citations_inv_re': related_citations_inv_re,
        'related_citations_as': related_citations_as,
    })
    return HttpResponse(template.render(context))


class IsisSearchView(FacetedSearchView):

    def build_page(self):
        """
        From haystacks SearchView:
        Paginates the results appropriately.
        In case someone does not want to use Django's built-in pagination, it
        should be a simple matter to override this method to do what they would
        like.
        """
        try:
            page_no = int(self.request.GET.get('page', 1))
        except (TypeError, ValueError):
            raise Http404("Not a valid number for page.")

        if page_no < 1:
            raise Http404("Pages should be 1 or greater.")

        start_offset = (page_no - 1) * self.results_per_page
        self.results[start_offset:start_offset + self.results_per_page]

        paginator = Paginator(self.results, self.results_per_page)


        try:
            page = paginator.page(page_no)
        except InvalidPage:
            try:
                page = paginator.page(1)
            except InvalidPage:
                raise Http404("No such page!")

        return (paginator, page)

    def extra_context(self):
        extra = super(FacetedSearchView, self).extra_context()
        extra['request'] = self.request
        extra['facets'] = self.results.facet_counts()
        extra['models'] = self.request.GET.getlist('models')
        extra['count'] = len(self.results)

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
