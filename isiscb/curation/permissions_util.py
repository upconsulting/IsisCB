from isisdata.models import Dataset, TenantRule
import curation.curation_util as c_util

import logging

logger = logging.getLogger(__name__)

def get_accessible_datasets(user):
    if user.is_superuser:
        return [ds.pk for ds in Dataset.objects.all()]

    roles = user.isiscb_roles.all()
    ds_roles = [rule for role in roles for rule in role.dataset_rules]

    # if user is not tenant admin and has no dataset rules
    # then they can view all tenant datasets (but not write to them)
    tenant = c_util.get_tenant(user)
    access = c_util.get_tenant_access(user, tenant) 
    if not ds_roles:
        if access: # access will be None if user does not have access to tenant
            return [dataset.pk for dataset in Dataset.objects.filter(owning_tenant=tenant)]
        return []
    
    # otherwise return all datasets in dataset rules
    return [int(role.dataset) if role.dataset else None for role in ds_roles]

def get_writable_datasets(user):
    if user.is_superuser:
        return [ds.pk for ds in Dataset.objects.all()]
    
    roles = user.isiscb_roles.all()
    ds_roles = [rule for role in roles for rule in role.dataset_rules]

    # if there are no dataset rules and user is tenant admin, 
    # then the user can write to all tenant datasets
    tenant = c_util.get_tenant(user)
    access = c_util.get_tenant_access(user, tenant)
    if not ds_roles and access == TenantRule.UPDATE:
        return [dataset.pk for dataset in Dataset.objects.filter(owning_tenant=tenant)]
    
    # if user is not tenant admin and has no dataset rules, then they should not be able
    # to write to anythin
    if not ds_roles:
        return []
    
    # else return list with all write permissions
    return [int(role.dataset) if role.dataset else None for role in ds_roles if role.can_write]

def get_accessible_dataset_objects(user):
    if user.is_superuser:
        return Dataset.objects.all()
    return Dataset.objects.filter(id__in=get_accessible_datasets(user))

def get_writable_dataset_objects(user):
    if user.is_superuser:
        return Dataset.objects.all()
    return Dataset.objects.filter(id__in=get_writable_datasets(user))