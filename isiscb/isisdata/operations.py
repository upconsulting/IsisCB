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
        # can_do_all = True
        return queryset

    _not_null = lambda obj: obj is not None and obj != ''
    # datasets = filter(_not_none, roles.filter(crudrule_set__crud_action=do).values_list('datasetrule_set__dataset_id', flat=True))
    # excluded_datasets = filter(_not_none, roles.filter(~Q(crudrule_set__crud_action=do)).values_list('datasetrule_set__dataset_id', flat=True))
    #
    #

    for rule in roles[0].accessrule_set.all():
        print rule.__dict__
    include = list(roles.filter(Q(accessrule__crudrule__crud_action=do)).values_list('accessrule__datasetrule__dataset', flat=True))
    include_isnull = '' in include or None in include
    include = filter(_not_null, include)
    print include
    exclude = list(roles.filter(~Q(accessrule__crudrule__crud_action=do)).values_list('accessrule__datasetrule__dataset', flat=True))
    exclude_isnull = '' in exclude or None in exclude
    exclude = filter(_not_null, exclude)
    print exclude


        # for role in roles:
        #
        #     # if there are dataset limitations in role
        #     can_do = role.crud_rules.filter(crud_action=do).count()
        #     if role.dataset_rules.count() > 0:
        #         no_dataset_in_role = role.dataset_rules.filter(dataset__isnull=True).count()
        #         # if the crud rules allow viewing records in datasets add them to included datasets
        #         # if do in crud_actions:
        #         if can_do:
        #             datasets += filter(_not_null, role.dataset_rules.values_list('dataset', flat=True))
        #             include_no_dataset = True if no_dataset_in_role else False
        #         # otherwise exclude datasets
        #         else:
        #             excluded_datasets += datasets_in_role
        #             exclude_no_datasets = True if no_dataset_in_role else False
        #     else:
        #         can_do_all = can_do
        #     print role


    if exclude:
        query = Q(belongs_to__in=exclude)
        if exclude_isnull:
            query |= Q(belongs_to__isnull=True)
        queryset = queryset.exclude(query)

    if include:
        query = Q(belongs_to__in=datasets)
        if include_isnull:
            query |= Q(belongs_to__isnull=True)
        queryset = queryset.filter(query)
    return queryset
