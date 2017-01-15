# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0050_auto_20161024_1447'),
    ]

    operations = [
        migrations.AlterField(
            model_name='citation',
            name='title_for_sort',
            field=models.CharField(db_index=True, max_length=2000, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='historicalcitation',
            name='title_for_sort',
            field=models.CharField(db_index=True, max_length=2000, null=True, blank=True),
        )
    ]
