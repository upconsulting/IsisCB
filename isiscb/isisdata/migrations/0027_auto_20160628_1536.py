# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0026_auto_20160628_1517'),
    ]

    operations = [
        migrations.AddField(
            model_name='isiscbrole',
            name='description',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='isiscbrole',
            name='name',
            field=models.CharField(max_length=255),
        ),
    ]
