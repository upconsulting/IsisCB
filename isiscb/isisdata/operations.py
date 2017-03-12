from django.db.models import Q

from isisdata.models import *


def filter_queryset(user, queryset, do=CRUDRule.VIEW):
    """
    Limit a :class:`.QuerySet` to what ``user`` has permission to ``do``.
    """
    roles = IsisCBRole.objects.filter(users__pk=user.pk)

    datasets = []
    include_no_dataset = False
    excluded_datasets = []
    exclude_no_datasets = False
    can_do_all = False

    if user.is_superuser:
        can_do_all = True
    else:
        for role in roles:
            # if there are dataset limitations in role
            if role.dataset_rules:
                crud_actions = [rule.crud_action for rule in role.crud_rules]
                datasets_in_role = [rule.dataset for rule in role.dataset_rules if rule.dataset]
                no_dataset_in_role = [None for rule in role.dataset_rules if not rule.dataset ]
                # if the crud rules allow viewing records in datasets add them to included datasets
                if do in crud_actions:
                    datasets += datasets_in_role
                    include_no_dataset = True if no_dataset_in_role else False
                # otherwise exclude datasets
                else:
                    excluded_datasets += datasets_in_role
                    exclude_no_datasets = True if no_dataset_in_role else False
            # if there are no dataset limitations
            else:
                crud_actions = [rule.crud_action for rule in role.crud_rules]
                if do in crud_actions:
                    can_do_all = True

    if excluded_datasets:
        query = Q(belongs_to__in=excluded_datasets)
        if exclude_no_datasets:
            query = query | Q(belongs_to__isnull=True)
        queryset = queryset.exclude(query)

    if not can_do_all:
        query = Q(belongs_to__in=datasets)
        if include_no_dataset:
            query = query | Q(belongs_to__isnull=True)
        queryset = queryset.filter(query)

    return queryset
