from django.shortcuts import get_object_or_404, render
from django.contrib.auth.models import User

from rest_framework import viewsets, serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from isisdata.models import *

from django.template import RequestContext, loader
from django.http import HttpResponse

from collections import defaultdict


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User


class AuthoritySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Authority


class CitationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Citation


class ACRelationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ACRelation


class CCRelationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CCRelation


class AARelationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = AARelation


class AttributeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Attribute


class LinkedDataSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = LinkedData


class AuthorityViewSet(viewsets.ModelViewSet):
    queryset = Authority.objects.all()
    serializer_class = AuthoritySerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class CitationViewSet(viewsets.ModelViewSet):
    queryset = Citation.objects.all()
    serializer_class = CitationSerializer


class ACRelationViewSet(viewsets.ModelViewSet):
    queryset = ACRelation.objects.all()
    serializer_class = ACRelationSerializer


class CCRelationViewSet(viewsets.ModelViewSet):
    queryset = CCRelation.objects.all()
    serializer_class = CCRelationSerializer


class AARelationViewSet(viewsets.ModelViewSet):
    queryset = AARelation.objects.all()
    serializer_class = AARelationSerializer


class AttributeViewSet(viewsets.ModelViewSet):
    queryset = Attribute.objects.all()
    serializer_class = AttributeSerializer


class LinkedDataViewSet(viewsets.ModelViewSet):
    queryset = LinkedData.objects.all()
    serializer_class = LinkedDataSerializer



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

def authority(request, authority_id):
    template = loader.get_template('isisdata/authority.html')
    authority = Authority.objects.get(id=authority_id)
    context = RequestContext(request, {
        'authority_id': authority_id,
        'authority': authority
    })
    return HttpResponse(template.render(context))

def citation(request, citation_id):
    template = loader.get_template('isisdata/citation.html')
    citation = get_object_or_404(Citation, pk=citation_id)
    authors = citation.acrelation_set.filter(type_controlled__in=['AU', 'CO'])

    properties = citation.acrelation_set.exclude(type_controlled__in=['AU', 'CO'])
    properties_map = defaultdict(list)
    for prop in properties:
        properties_map[prop.type_controlled] += [prop]

    context = RequestContext(request, {
        'citation_id': citation_id,
        'citation': citation,
        'authors': authors,
        'properties_map': properties
    })
    return HttpResponse(template.render(context))
