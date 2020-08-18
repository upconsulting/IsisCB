# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0030_auto_20160628_2057'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccessRule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, null=True, blank=True)),
                ('object_type', models.CharField(blank=True, max_length=255, null=True, choices=[(b'citation', b'Citation'), (b'authority', b'Authority')])),
                ('role', models.ForeignKey(blank=True, to='isisdata.IsisCBRole', help_text=b'The role a rules belongs to.', null=True, on_delete=models.CASCADE)),
            ],
        ),
        migrations.RemoveField(
            model_name='crudrule',
            name='id',
        ),
        migrations.RemoveField(
            model_name='crudrule',
            name='name',
        ),
        migrations.RemoveField(
            model_name='crudrule',
            name='object_type',
        ),
        migrations.RemoveField(
            model_name='crudrule',
            name='role',
        ),
        migrations.RemoveField(
            model_name='datasetrule',
            name='id',
        ),
        migrations.RemoveField(
            model_name='datasetrule',
            name='name',
        ),
        migrations.RemoveField(
            model_name='datasetrule',
            name='object_type',
        ),
        migrations.RemoveField(
            model_name='datasetrule',
            name='role',
        ),
        migrations.RemoveField(
            model_name='fieldrule',
            name='id',
        ),
        migrations.RemoveField(
            model_name='fieldrule',
            name='name',
        ),
        migrations.RemoveField(
            model_name='fieldrule',
            name='object_type',
        ),
        migrations.RemoveField(
            model_name='fieldrule',
            name='role',
        ),
        migrations.AlterField(
            model_name='fieldrule',
            name='field_action',
            field=models.CharField(max_length=255, choices=[(b'cannot_view', b'Cannot View'), (b'cannot_update', b'Cannot Update')]),
        ),
        migrations.AddField(
            model_name='crudrule',
            name='accessrule_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, default='0', serialize=False, to='isisdata.AccessRule', on_delete=models.CASCADE),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='datasetrule',
            name='accessrule_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, default='0', serialize=False, to='isisdata.AccessRule', on_delete=models.CASCADE),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='fieldrule',
            name='accessrule_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, default='0', serialize=False, to='isisdata.AccessRule', on_delete=models.CASCADE),
            preserve_default=False,
        ),
    ]
