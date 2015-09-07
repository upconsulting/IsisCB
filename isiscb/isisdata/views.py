from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.contrib.auth.models import User
from django.db import connection
from django.http import HttpResponse

from rest_framework import viewsets, serializers, mixins
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from isisdata.models import *

from django.template import RequestContext, loader
from django.http import HttpResponse

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

# class ReferencedEntityRelatedField(serializers.HyperlinkedRelatedField):
#     view_name = ''
#
#     def to_representation(self, value):
#         print self.view_name
#         if hasattr(value, 'citation'):
#             self.view_name = 'citation-detail'
#             value = value.citation
#         if hasattr(value, 'authority'):
#             self.view_name = 'authority-detail'
#             value = value.citation
#         return super(ReferencedEntityRelatedField, self).to_representation(value)


class AttributeViewSet(mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       viewsets.GenericViewSet):

    queryset = Attribute.objects.all()
    serializer_class = AttributeSerializer
    # source = ReferencedEntityRelatedField(read_only=True)


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

def index(request, obj_id):
    template = loader.get_template('isisdata/index.html')
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
        citations_by = citations_by_paginator.page(page_other)
    except PageNotAnInteger:
        citations_by = citations_by_paginator.page(1)
    except EmptyPage:
        citations_by = citations_by_paginator.page(paginator.num_pages)

    context = RequestContext(request, {
        'authority_id': authority_id,
        'authority': authority,
        'citations_by': citations_by,
        'citations_about': citations_about,
        'citations_other': citations_other
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
    })
    return HttpResponse(template.render(context))
