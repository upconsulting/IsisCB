# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-07-28 01:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zotero', '0019_auto_20170508_1734'),
    ]

    operations = [
        migrations.AddField(
            model_name='draftcitation',
            name='extent_note',
            field=models.TextField(blank=True, null=True),
        ),
    ]
