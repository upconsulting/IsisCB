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
from django.conf import settings
from django.contrib import admin
from django.views.generic.base import RedirectView
from django.contrib.auth import views as auth_views
from rest_framework import routers
from oauth2_provider import views as oauth_views

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
    url(r'^(?i)rest/$', views.api_root, name='rest_root'),
    url(r'^(?i)rest/', include(router.urls)),
    url(r'^(?i)rest/auth/$', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^(?i)admin/', include(admin.site.urls)),
    url(r'^(?i)isis/', include('isisdata.urls')),
    url(r'^(?i)zotero/', include('zotero.urls')),
    url(r'^(?i)history/$', views.search_history, name='search_history'),
    url(r'^(?i)history/saved/$', views.search_saved, name='search_saved'),
    url(r'^$', views.home, name='home'),
    url(r'^$', RedirectView.as_view(url='isis/', permanent=False), name='index'),
    url(r'^(?i)autocomplete/', include('autocomplete_light.urls')),
    url(r'^(?i)login/$',  # TODO: can we simplify this?
                auth_views.login,
                name='login'),
    url(r'^(?i)logout/$',  # TODO: can we simplify this?
                auth_views.logout,
                name='logout'),
    url(r'^(?i)password/change/$',  # TODO: can we simplify this?
                auth_views.password_change,
                name='password_change'),
    url(r'^(?i)password/change/done/$',
                auth_views.password_change_done,
                name='password_change_done'),
    url(r'^(?i)password/reset/$',
                auth_views.password_reset,
                {'from_email': settings.SMTP_EMAIL},
                name='password_reset'),
    url(r'^(?i)password/reset/done/$',
                auth_views.password_reset_done,
                name='password_reset_done'),
    url(r'^(?i)password/reset/complete/$',
                auth_views.password_reset_complete,
                name='password_reset_complete'),
    url(r'^(?i)password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
                auth_views.password_reset_confirm,
                name='password_reset_confirm'),
    url(r'^(?i)register/$', views.UserRegistrationView.as_view()),

    # url(r'^(?i)accounts/', include('registration.backends.simple.urls')),
    url(r'^(?i)captcha/', include('captcha.urls')),

    # We define the following oauth2 views explicitly to disable insecure
    #  features. See https://github.com/evonove/django-oauth-toolkit/issues/196
    url(r'^(?i)o/authorize/$',
                oauth_views.AuthorizationView.as_view(),
                name="authorize"),
    url(r'^(?i)o/token/$', oauth_views.TokenView.as_view(),
                name="token"),
    url(r'^(?i)o/revoke_token/$',
                oauth_views.RevokeTokenView.as_view(),
                name="revoke-token"),

    # Social authentication views.
    url('', include('social.apps.django_app.urls', namespace='social')),

]
