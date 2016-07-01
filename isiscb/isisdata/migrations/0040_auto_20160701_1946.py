# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0039_auto_20160701_1900'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalperson',
            name='personal_name_first',
            field=models.CharField(max_length=255, blank=True),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='personal_name_last',
            field=models.CharField(max_length=255, blank=True),
        ),
        migrations.AlterField(
            model_name='person',
            name='personal_name_first',
            field=models.CharField(max_length=255, blank=True),
        ),
        migrations.AlterField(
            model_name='person',
            name='personal_name_last',
            field=models.CharField(max_length=255, blank=True),
        ),
    ]
