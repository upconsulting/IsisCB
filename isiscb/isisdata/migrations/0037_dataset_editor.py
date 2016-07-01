# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0036_auto_20160701_1459'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='editor',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
