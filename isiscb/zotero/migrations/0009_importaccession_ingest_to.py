# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0038_auto_20160701_1552'),
        ('zotero', '0008_importaccession_resolved'),
    ]

    operations = [
        migrations.AddField(
            model_name='importaccession',
            name='ingest_to',
            field=models.ForeignKey(to='isisdata.Dataset', null=True, on_delete=models.CASCADE),
        ),
    ]
