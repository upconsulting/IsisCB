import django_filters
from django.contrib.auth.models import User
from isisdata.models import IsisCBRole, CitationCollection


class UserFilter(django_filters.FilterSet):
    username = django_filters.CharFilter(lookup_expr='icontains')
    roles = django_filters.ModelChoiceFilter(name='isiscbrole', queryset=IsisCBRole.objects.all())

    class Meta:
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

    class Meta:
        model = CitationCollection
        fields = ('name', 'createdBy')
