# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('zotero', '0010_remove_importaccession_resolved'),
    ]

    operations = [
        migrations.AddField(
            model_name='importaccession',
            name='processed',
            field=models.BooleanField(default=False),
        ),
    ]
