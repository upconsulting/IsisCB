"""isiscb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/

"""
from __future__ import unicode_literals
from django.conf.urls import include, url
from django.conf import settings
from django.contrib import admin
from django.views.generic.base import RedirectView
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from rest_framework import routers
from oauth2_provider import views as oauth_views
from django.urls import path, re_path
from django.conf import settings
from django.conf.urls.static import static

from isisdata import views, account_views

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
router.register('comment', views.CommentViewSet)

urlpatterns = [
    re_path(r'^rest/$', views.api_root, name='rest_root'),
    re_path(r'^rest/', include(router.urls)),
    re_path(r'^rest/auth/', include('rest_framework.urls', namespace='rest_framework')),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^zotero/', include('zotero.urls')),
    re_path(r'^user/(?P<username>[^/]+)/$', views.user_profile, name='user_profile'),
    re_path(r'^history/', views.search_history, name='search_history'),
    re_path(r'^history/saved/', views.search_saved, name='search_saved'),
    re_path(r'^$', views.home, name='home'),
    re_path(r'^$', RedirectView.as_view(url='isis/', permanent=False), name='index'),
    re_path(r'^robots\.txt', TemplateView.as_view(template_name='isisdata/robots.txt', content_type='text/plain'), name="robots"),
    re_path(r'^captcha/', include('captcha.urls')),

    re_path(r'^curation/', include('curation.urls')),
    re_path(r'^'+settings.PORTAL_PREFIX+'/', include('tenants.urls', namespace="tenants")),
    re_path(r'^portal/', include('tenants.urls', namespace="tenants")),
    re_path(r'^isis/', include('isisdata.urls')),
    re_path('password/change/', account_views.PasswordChangeView.as_view(), name="account_change_password"),
    re_path('', include('allauth.urls')),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

