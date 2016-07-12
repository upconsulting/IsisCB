# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0040_auto_20160701_1946'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aarelation',
            name='record_status_value',
            field=models.CharField(default=b'Active', max_length=255, null=True, blank=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='acrelation',
            name='record_status_value',
            field=models.CharField(default=b'Active', max_length=255, null=True, blank=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='attribute',
            name='record_status_value',
            field=models.CharField(default=b'Active', max_length=255, null=True, blank=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='authority',
            name='record_status_value',
            field=models.CharField(default=b'Active', max_length=255, null=True, blank=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='ccrelation',
            name='record_status_value',
            field=models.CharField(default=b'Active', max_length=255, null=True, blank=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='citation',
            name='record_status_value',
            field=models.CharField(default=b'Active', max_length=255, null=True, blank=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='dataset',
            name='record_status_value',
            field=models.CharField(default=b'Active', max_length=255, null=True, blank=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicalacrelation',
            name='record_status_value',
            field=models.CharField(default=b'Active', max_length=255, null=True, blank=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicalattribute',
            name='record_status_value',
            field=models.CharField(default=b'Active', max_length=255, null=True, blank=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='record_status_value',
            field=models.CharField(default=b'Active', max_length=255, null=True, blank=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicalccrelation',
            name='record_status_value',
            field=models.CharField(default=b'Active', max_length=255, null=True, blank=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicalcitation',
            name='record_status_value',
            field=models.CharField(default=b'Active', max_length=255, null=True, blank=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicallinkeddata',
            name='record_status_value',
            field=models.CharField(default=b'Active', max_length=255, null=True, blank=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='record_status_value',
            field=models.CharField(default=b'Active', max_length=255, null=True, blank=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicaltracking',
            name='record_status_value',
            field=models.CharField(default=b'Active', max_length=255, null=True, blank=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='linkeddata',
            name='record_status_value',
            field=models.CharField(default=b'Active', max_length=255, null=True, blank=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='tracking',
            name='record_status_value',
            field=models.CharField(default=b'Active', max_length=255, null=True, blank=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='bio_markup_type',
            field=models.CharField(default=b'markdown', max_length=30, editable=False, choices=[(b'', b'--'), (b'markdown', b'markdown')]),
        ),
    ]
