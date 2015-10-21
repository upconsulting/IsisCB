# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0002_attributetype_display_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='acrelation',
            name='data_display_order',
            field=models.FloatField(default=1.0, help_text=b'\n    Position on which the authority should be displayed.'),
        ),
        migrations.AddField(
            model_name='acrelation',
            name='name_as_entered',
            field=models.CharField(help_text=b'\n    Display for the authority as it is has been used in a publication.', max_length=255, blank=True),
        ),
        migrations.AddField(
            model_name='historicalacrelation',
            name='data_display_order',
            field=models.FloatField(default=1.0, help_text=b'\n    Position on which the authority should be displayed.'),
        ),
        migrations.AddField(
            model_name='historicalacrelation',
            name='name_as_entered',
            field=models.CharField(help_text=b'\n    Display for the authority as it is has been used in a publication.', max_length=255, blank=True),
        ),
    ]
