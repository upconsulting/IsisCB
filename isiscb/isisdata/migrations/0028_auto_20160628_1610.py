# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0027_auto_20160628_1536'),
    ]

    operations = [
        migrations.AddField(
            model_name='datasetrule',
            name='object_type',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'citation', b'Citation'), (b'authority', b'Authority')]),
        ),
        migrations.AddField(
            model_name='fieldrule',
            name='object_type',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'citation', b'Citation'), (b'authority', b'Authority')]),
        ),
    ]
