from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings



os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isiscb.production_settings')
app = Celery('isiscb')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
# app.conf.broker_url = 'redis://localhost:6379/0'
# app.conf.result_backend = 'django-db'
# app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)



@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
