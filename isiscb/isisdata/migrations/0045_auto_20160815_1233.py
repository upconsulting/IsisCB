# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0044_auto_20160809_1229'),
    ]

    operations = [
        migrations.AddField(
            model_name='authority',
            name='name_for_sort',
            field=models.CharField(max_length=2000, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='historicalauthority',
            name='name_for_sort',
            field=models.CharField(max_length=2000, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='historicalperson',
            name='name_for_sort',
            field=models.CharField(max_length=2000, null=True, blank=True),
        ),
    ]
