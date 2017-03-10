# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0055_auto_20170221_1455'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicaltracking',
            name='subject_instance_id',
            field=models.CharField(max_length=200, db_index=True),
        ),
        migrations.AlterField(
            model_name='tracking',
            name='subject_instance_id',
            field=models.CharField(max_length=200, db_index=True),
        ),
    ]
