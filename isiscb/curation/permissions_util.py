from isisdata.models import Dataset

def get_accessible_datasets(user):
    roles = user.isiscb_roles.all()
    ds_roles = [rule for role in roles for rule in role.dataset_rules]
    return [int(role.dataset) for role in ds_roles]

def get_writable_datasets(user):
    roles = user.isiscb_roles.all()
    ds_roles = [rule for role in roles for rule in role.dataset_rules]
    # if there are no dataset rules, then the user has access to everything
    if not ds_roles:
        return None
    # else an empty list indicates that there are dataset restrictions but no write permissions
    return [int(role.dataset) for role in ds_roles if role.can_write]

def get_accessible_dataset_objects(user):
    if user.is_superuser:
        return Dataset.objects.all()
    return Dataset.objects.filter(id__in=get_accessible_datasets(user))

def get_writable_dataset_objects(user):
    if user.is_superuser:
        return Dataset.objects.all()
    return Dataset.objects.filter(id__in=get_writable_datasets(user))