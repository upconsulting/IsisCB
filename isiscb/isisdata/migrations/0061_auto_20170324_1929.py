# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-24 19:29
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0060_auto_20170324_1741'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historicaltracking',
            name='subject_content_type',
        ),
        migrations.RemoveField(
            model_name='historicaltracking',
            name='subject_instance_id',
        ),
        migrations.RemoveField(
            model_name='tracking',
            name='subject_content_type',
        ),
        migrations.RemoveField(
            model_name='tracking',
            name='subject_instance_id',
        ),
    ]
