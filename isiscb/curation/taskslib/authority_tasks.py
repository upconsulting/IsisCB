from celery import shared_task

from isisdata.models import Authority

@shared_task
def add_attributes_to_authority(file, task_id):
    # do something
    print file
    print task_id
