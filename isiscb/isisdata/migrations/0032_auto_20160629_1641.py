# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0031_auto_20160629_0204'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserModuleRule',
            fields=[
                ('accessrule_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='isisdata.AccessRule', on_delete=models.CASCADE)),
                ('module_action', models.CharField(max_length=255, choices=[(b'view', b'View'), (b'update', b'Update')])),
            ],
            bases=('isisdata.accessrule',),
        ),
        migrations.AlterModelOptions(
            name='isodaterangevalue',
            options={'verbose_name': 'ISO date range'},
        ),
    ]
