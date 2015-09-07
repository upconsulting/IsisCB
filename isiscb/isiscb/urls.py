"""isiscb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic.base import RedirectView

from rest_framework import routers

from isisdata import views

router = routers.SimpleRouter()
router.register('authority', views.AuthorityViewSet)
router.register('citation', views.CitationViewSet)
router.register('acrelation', views.ACRelationViewSet)
router.register('ccrelation', views.CCRelationViewSet)
router.register('aarelation', views.AARelationViewSet)
router.register('attribute', views.AttributeViewSet)
router.register('linkeddata', views.LinkedDataViewSet)
router.register('linkeddatatype', views.LinkedDataTypeViewSet)
router.register('value', views.ValueViewSet)
router.register('language', views.LanguageViewSet)
router.register('partdetails', views.PartDetailsViewSet)
router.register('attributetype', views.AttributeTypeViewSet)
router.register('contenttype', views.ContentTypeViewSet)
router.register('user', views.UserViewSet)

urlpatterns = [
    url(r'^rest/$', views.api_root),
    url(r'^rest/', include(router.urls)),
    url(r'^rest/auth/$', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^isis/', include('isisdata.urls')),
    url(r'^$', RedirectView.as_view(url='isis/', permanent=False), name='index'),
    url(r'^autocomplete/', include('autocomplete_light.urls')),
    url(r'^', include('registration.backends.simple.urls')),
    # url('^', include('django.contrib.auth.urls'))
]
