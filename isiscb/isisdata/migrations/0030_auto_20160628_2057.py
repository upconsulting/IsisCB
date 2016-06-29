# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0029_auto_20160628_1954'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='fieldrule',
            name='is_accessible',
        ),
        migrations.AddField(
            model_name='fieldrule',
            name='field_action',
            field=models.CharField(default='VIEW', max_length=255, choices=[(b'view', b'View'), (b'update', b'Update')]),
            preserve_default=False,
        ),
    ]
