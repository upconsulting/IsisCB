# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-04-27 15:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0018_auto_20160425_1334'),
    ]

    operations = [
        migrations.AlterField(
            model_name='acrelation',
            name='type_broad_controlled',
            field=models.CharField(blank=True, choices=[(b'PR', b'Has Personal Responsibility For'), (b'SC', b'Provides Subject Content About'), (b'IH', b'Is Institutional Host Of'), (b'PH', b'Is Publication Host Of')], help_text=b'Used to specify the nature of the relationship between authority (as the subject) and the citation (as the object) more broadly than the relationship type.', max_length=2, null=True, verbose_name=b'relationship type (broad)'),
        ),
        migrations.AlterField(
            model_name='historicalacrelation',
            name='type_broad_controlled',
            field=models.CharField(blank=True, choices=[(b'PR', b'Has Personal Responsibility For'), (b'SC', b'Provides Subject Content About'), (b'IH', b'Is Institutional Host Of'), (b'PH', b'Is Publication Host Of')], help_text=b'Used to specify the nature of the relationship between authority (as the subject) and the citation (as the object) more broadly than the relationship type.', max_length=2, null=True, verbose_name=b'relationship type (broad)'),
        ),
    ]
