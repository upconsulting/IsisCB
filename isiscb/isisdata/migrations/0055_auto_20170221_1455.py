# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0054_auto_20170205_2248'),
    ]

    operations = [
        migrations.CreateModel(
            name='AsyncTask',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('async_uuid', models.CharField(max_length=255, null=True, blank=True)),
                ('max_value', models.FloatField(default=0.0)),
                ('current_value', models.FloatField(default=0.0)),
                ('state', models.CharField(max_length=10, null=True, blank=True)),
                ('_value', models.TextField()),
            ],
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='bio_markup_type',
            field=models.CharField(default=b'markdown', max_length=30, editable=False, choices=[(b'', b'--'), (b'markdown', b'markdown')]),
        ),
    ]
