# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-05-08 17:34
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zotero', '0018_auto_20170205_2354'),
    ]

    operations = [
        migrations.AlterField(
            model_name='draftauthority',
            name='type_controlled',
            field=models.CharField(blank=True, choices=[('PE', 'Person'), ('IN', 'Institution'), ('TI', 'Time Period'), ('GE', 'Geographic Term'), ('SE', 'Serial Publication'), ('CT', 'Classification Term'), ('CO', 'Concept'), ('CW', 'Creative Work'), ('EV', 'Event'), ('CR', 'Cross-reference')], max_length=2, null=True),
        ),
    ]
