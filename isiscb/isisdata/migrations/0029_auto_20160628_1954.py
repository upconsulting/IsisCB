# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0028_auto_20160628_1610'),
    ]

    operations = [
        migrations.AlterField(
            model_name='crudrule',
            name='crud_action',
            field=models.CharField(max_length=255, choices=[(b'create', b'Create'), (b'view', b'View'), (b'update', b'Update'), (b'delete', b'Delete')]),
        ),
    ]
