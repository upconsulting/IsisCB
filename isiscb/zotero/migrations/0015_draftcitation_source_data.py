# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('zotero', '0014_auto_20161024_1447'),
    ]

    operations = [
        migrations.AddField(
            model_name='draftcitation',
            name='source_data',
            field=models.TextField(null=True, blank=True),
        ),
    ]
