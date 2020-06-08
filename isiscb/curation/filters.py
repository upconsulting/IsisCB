from __future__ import unicode_literals
from builtins import object
import django_filters
from django.contrib.auth.models import User
from isisdata.models import IsisCBRole, CitationCollection, AuthorityCollection
from unidecode import unidecode

class UserFilter(django_filters.FilterSet):
    username = django_filters.CharFilter(lookup_expr='icontains')
    roles = django_filters.ModelChoiceFilter(field_name='isiscbrole', queryset=IsisCBRole.objects.all())

    class Meta(object):
        model = User
        fields = [
            'username', 'roles', 'is_staff'
        ]
    o = django_filters.filters.OrderingFilter(
        # tuple-mapping retains order
        fields=(
            ('username', 'username'),
            ('email', 'email'),
            ('isiscbrole', 'role'),
        ),

        # labels do not need to retain order
        field_labels={
            'username': 'Username',
        }
    )


class CitationCollectionFilter(django_filters.FilterSet):
    createdBy = django_filters.ModelChoiceFilter(queryset=User.objects.filter(citation_collections__id__isnull=False).distinct('id'))

    class Meta(object):
        model = CitationCollection
        fields = ('name', 'createdBy')

class AuthorityCollectionFilter(django_filters.FilterSet):
    createdBy = django_filters.ModelChoiceFilter(queryset=User.objects.filter(authority_collections__id__isnull=False).distinct('id'))
    name = django_filters.CharFilter(method='filter_name')

    class Meta(object):
        model = AuthorityCollection
        fields = ('name', 'createdBy')

    def filter_name(self, queryset, name, value):
        value = unidecode(value)
        if not value:
            return queryset
        for part in value.split():
            queryset = queryset.filter(name__icontains=part)

        return queryset
