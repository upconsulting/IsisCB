# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-04-02 04:00
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0073_auto_20180304_0254'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuthorityValue',
            fields=[
                ('value_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='isisdata.Value')),
                ('value', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='isisdata.Authority')),
            ],
            options={
                'verbose_name': 'authority',
            },
            bases=('isisdata.value',),
        ),
    ]
