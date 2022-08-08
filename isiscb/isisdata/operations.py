from __future__ import unicode_literals
from builtins import filter
from django.db.models import Q

from isisdata.models import *


def filter_queryset(user, queryset, do=CRUDRule.VIEW):
    return queryset
    
    """
    Limit a :class:`.QuerySet` to what ``user`` has permission to ``do``.
    """
    roles = user.isiscbrole_set.all()

    if user.is_superuser:    # Superusers are super users.
        return queryset

    _not_null = lambda obj: obj is not None and obj != ''

    # Identify roles that explicitly grant or implicitly deny permission to
    #  ``do``.
    do_pks = roles.filter(Q(accessrule__crudrule__crud_action=do)).values_list('id', flat=True)
    dont_pks = roles.filter(~Q(accessrule__crudrule__crud_action=do)).values_list('id', flat=True)

    # We need a separate query here, since those above are inner joins and
    #  we want access to adjacent accessrule entries rooted in the same role.
    include = list(roles.filter(pk__in=do_pks, accessrule__datasetrule__isnull=False).values_list('accessrule__datasetrule__dataset', flat=True))
    exclude = list(roles.filter(pk__in=dont_pks, accessrule__datasetrule__isnull=False).values_list('accessrule__datasetrule__dataset', flat=True))

    # Some citations and authorities are not assigned to a dataset. So if the
    #  dataset is not set, then the rule applies to records without a dataset.
    include_isnull = '' in include or None in include
    exclude_isnull = '' in exclude or None in exclude

    # We can't use null values when filtering, below.
    include = list(filter(_not_null, include))
    exclude = list(filter(_not_null, exclude))

    if exclude or exclude_isnull:
        query = Q(belongs_to__in=exclude)
        if exclude_isnull:
            query |= Q(belongs_to__isnull=True)
        queryset = queryset.exclude(query)

    # If ``include`` is empty, this will have the effect of excluding all
    #  records, unless ``include_isnull`` is True and the record has no dataset.
    query = Q(belongs_to__in=include)
    if include_isnull:
        query |= Q(belongs_to__isnull=True)
    queryset = queryset.filter(query)
    return queryset
