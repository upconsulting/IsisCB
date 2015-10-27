# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0006_auto_20151027_1702'),
    ]

    operations = [
        migrations.AddField(
            model_name='aarelation',
            name='public',
            field=models.BooleanField(default=True, help_text=b'\n    Controls whether this instance can be viewed by end users.'),
        ),
        migrations.AddField(
            model_name='acrelation',
            name='public',
            field=models.BooleanField(default=True, help_text=b'\n    Controls whether this instance can be viewed by end users.'),
        ),
        migrations.AddField(
            model_name='attribute',
            name='public',
            field=models.BooleanField(default=True, help_text=b'\n    Controls whether this instance can be viewed by end users.'),
        ),
        migrations.AddField(
            model_name='authority',
            name='public',
            field=models.BooleanField(default=True, help_text=b'\n    Controls whether this instance can be viewed by end users.'),
        ),
        migrations.AddField(
            model_name='ccrelation',
            name='public',
            field=models.BooleanField(default=True, help_text=b'\n    Controls whether this instance can be viewed by end users.'),
        ),
        migrations.AddField(
            model_name='citation',
            name='public',
            field=models.BooleanField(default=True, help_text=b'\n    Controls whether this instance can be viewed by end users.'),
        ),
        migrations.AddField(
            model_name='historicalacrelation',
            name='public',
            field=models.BooleanField(default=True, help_text=b'\n    Controls whether this instance can be viewed by end users.'),
        ),
        migrations.AddField(
            model_name='historicalattribute',
            name='public',
            field=models.BooleanField(default=True, help_text=b'\n    Controls whether this instance can be viewed by end users.'),
        ),
        migrations.AddField(
            model_name='historicalauthority',
            name='public',
            field=models.BooleanField(default=True, help_text=b'\n    Controls whether this instance can be viewed by end users.'),
        ),
        migrations.AddField(
            model_name='historicalccrelation',
            name='public',
            field=models.BooleanField(default=True, help_text=b'\n    Controls whether this instance can be viewed by end users.'),
        ),
        migrations.AddField(
            model_name='historicalcitation',
            name='public',
            field=models.BooleanField(default=True, help_text=b'\n    Controls whether this instance can be viewed by end users.'),
        ),
        migrations.AddField(
            model_name='historicallinkeddata',
            name='public',
            field=models.BooleanField(default=True, help_text=b'\n    Controls whether this instance can be viewed by end users.'),
        ),
        migrations.AddField(
            model_name='historicalperson',
            name='public',
            field=models.BooleanField(default=True, help_text=b'\n    Controls whether this instance can be viewed by end users.'),
        ),
        migrations.AddField(
            model_name='historicaltracking',
            name='public',
            field=models.BooleanField(default=True, help_text=b'\n    Controls whether this instance can be viewed by end users.'),
        ),
        migrations.AddField(
            model_name='linkeddata',
            name='public',
            field=models.BooleanField(default=True, help_text=b'\n    Controls whether this instance can be viewed by end users.'),
        ),
        migrations.AddField(
            model_name='tracking',
            name='public',
            field=models.BooleanField(default=True, help_text=b'\n    Controls whether this instance can be viewed by end users.'),
        ),
    ]
