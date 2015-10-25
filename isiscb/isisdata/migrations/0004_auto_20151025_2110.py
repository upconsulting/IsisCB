# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0003_add_acrelation_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='acrelation',
            name='data_display_order',
            field=models.FloatField(default=1.0, help_text=b'\n    Position at which the authority should be displayed.'),
        ),
        migrations.AlterField(
            model_name='historicalacrelation',
            name='data_display_order',
            field=models.FloatField(default=1.0, help_text=b'\n    Position at which the authority should be displayed.'),
        ),
    ]
