# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-09-04 08:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zotero', '0022_auto_20170728_0129'),
    ]

    operations = [
        migrations.AddField(
            model_name='draftacrelation',
            name='data_display_order',
            field=models.FloatField(default=1.0),
        ),
    ]
