from django.conf.urls import include, url

from curation import views


urlpatterns = [
    url(r'^(?i)dashboard/$', views.dashboard, name='dashboard'),
]
