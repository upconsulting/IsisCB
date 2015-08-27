from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^authority/(?P<authority_id>[A-Z]+[0-9]+)/$', views.authority, name='authority'),
    url(r'^citation/(?P<citation_id>[A-Z]+[0-9]+)/$', views.citation, name='citation')
]
