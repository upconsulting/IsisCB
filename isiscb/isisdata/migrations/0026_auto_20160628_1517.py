# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('isisdata', '0025_isodaterangevalue'),
    ]

    operations = [
        migrations.CreateModel(
            name='CRUDRule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, null=True, blank=True)),
                ('crud_action', models.CharField(blank=True, max_length=255, null=True, choices=[(b'create', b'Create'), (b'view', b'View'), (b'update', b'Update'), (b'delete', b'Delete')])),
                ('object_type', models.CharField(blank=True, max_length=255, null=True, choices=[(b'citation', b'Citation'), (b'authority', b'Authority')])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DatasetRule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, null=True, blank=True)),
                ('dataset', models.CharField(max_length=255)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FieldRule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, null=True, blank=True)),
                ('field_name', models.CharField(max_length=255)),
                ('is_accessible', models.BooleanField(default=True, help_text=b'Controls whether a user has access to the specified field.')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='IsisCBRole',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, null=True, blank=True)),
                ('users', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterField(
            model_name='aarelation',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='acrelation',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='attribute',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='authority',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='ccrelation',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='citation',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicalacrelation',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicalattribute',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicalccrelation',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicalcitation',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicallinkeddata',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicaltracking',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='linkeddata',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='tracking',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='bio_markup_type',
            field=models.CharField(default=b'markdown', max_length=30, editable=False, choices=[(b'', b'--'), (b'html', 'HTML'), (b'plain', 'Plain'), (b'markdown', 'Markdown')]),
        ),
        migrations.AddField(
            model_name='fieldrule',
            name='role',
            field=models.ForeignKey(blank=True, to='isisdata.IsisCBRole', help_text=b'The role a rules belongs to.', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='datasetrule',
            name='role',
            field=models.ForeignKey(blank=True, to='isisdata.IsisCBRole', help_text=b'The role a rules belongs to.', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='crudrule',
            name='role',
            field=models.ForeignKey(blank=True, to='isisdata.IsisCBRole', help_text=b'The role a rules belongs to.', null=True, on_delete=models.CASCADE),
        ),
    ]
