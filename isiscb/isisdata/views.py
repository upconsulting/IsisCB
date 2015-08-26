from django.shortcuts import render
from django.contrib.auth.models import User
from django.db import connection
from django.http import HttpResponse

from rest_framework import viewsets, serializers, mixins
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from isisdata.models import *

def ackview(request, id, *args, **kwargs):
    return HttpResponse(Authority.objects.get(pk=id).name)


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
