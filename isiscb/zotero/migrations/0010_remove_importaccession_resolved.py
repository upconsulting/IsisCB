# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('zotero', '0009_importaccession_ingest_to'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='importaccession',
            name='resolved',
        ),
    ]
