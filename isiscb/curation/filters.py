import django_filters

from isisdata.models import Citation


class Citation(filters.FilterSet):
    name = django_filters.CharFilter(name='name', lookup_type='icontains')

    class Meta:
        model = Citation
        fields = ['name',]
