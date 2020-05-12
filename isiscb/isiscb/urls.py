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
router.register('comment', views.CommentViewSet)

urlpatterns = [
    re_path(r'^(?i)rest/', views.api_root, name='rest_root'),
    re_path(r'^(?i)rest/', include(router.urls)),
    re_path(r'^(?i)rest/auth/', include('rest_framework.urls', namespace='rest_framework')),
    re_path(r'^(?i)admin/', admin.site.urls),
    re_path(r'^(?i)isis/', include('isisdata.urls')),
    re_path(r'^(?i)zotero/', include('zotero.urls')),
    re_path(r'^(?i)history/', views.search_history, name='search_history'),
    re_path(r'^(?i)history/saved/', views.search_saved, name='search_saved'),
    re_path(r'^', views.home, name='home'),
    re_path(r'^robots\.txt', TemplateView.as_view(template_name='isisdata/robots.txt', content_type='text/plain'), name="robots"),
    re_path(r'^', RedirectView.as_view(url='isis/', permanent=False), name='index'),
    
    re_path(r'^(?i)login/',  # TODO: can we simplify this?
                auth_views.LoginView,
                name='login'),
    re_path(r'^(?i)logout/',  # TODO: can we simplify this?
                auth_views.LogoutView,
                name='logout'),
    re_path(r'^(?i)password/change/',  # TODO: can we simplify this?
                auth_views.PasswordChangeView,
                name='password_change'),
    re_path(r'^(?i)password/change/done/',
                auth_views.PasswordChangeDoneView,
                name='password_change_done'),
    re_path(r'^(?i)password/reset/',
                auth_views.PasswordResetView,
                {'from_email': settings.SMTP_EMAIL},
                name='password_reset'),
    re_path(r'^(?i)password/reset/done/',
                auth_views.PasswordResetDoneView,
                name='password_reset_done'),
    re_path(r'^(?i)password/reset/complete/',
                auth_views.PasswordResetCompleteView,
                name='password_reset_complete'),
    re_path(r'^(?i)password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/',
                auth_views.PasswordResetConfirmView,
                name='password_reset_confirm'),
    re_path(r'^(?i)register/', views.UserRegistrationView.as_view()),

    # url(r'^(?i)accounts/', include('registration.backends.simple.urls')),
    re_path(r'^(?i)captcha/', include('captcha.urls')),

    # We define the following oauth2 views explicitly to disable insecure
    #  features. See https://github.com/evonove/django-oauth-toolkit/issues/196
    re_path(r'^(?i)o/authorize/',
                oauth_views.AuthorizationView.as_view(),
                name="authorize"),
    re_path(r'^(?i)o/token/', oauth_views.TokenView.as_view(),
                name="token"),
    re_path(r'^(?i)o/revoke_token/',
                oauth_views.RevokeTokenView.as_view(),
                name="revoke-token"),

    re_path(r'^curation/', include('curation.urls')),
    # Social authentication views.
    re_path('', include('social_django.urls', namespace='social')),

]
