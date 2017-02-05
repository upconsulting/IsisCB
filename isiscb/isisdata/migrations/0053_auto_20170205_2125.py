# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0052_auto_20170205_2120'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasetrule',
            name='dataset',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]
