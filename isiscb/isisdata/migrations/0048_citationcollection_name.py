# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0047_auto_20160823_0103'),
    ]

    operations = [
        migrations.AddField(
            model_name='citationcollection',
            name='name',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]
