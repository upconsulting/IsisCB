# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('zotero', '0013_populate_draftauthority_name_for_sort'),
    ]

    operations = [
        migrations.AddField(
            model_name='draftcitation',
            name='book_series',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='draftcitation',
            name='extent',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
    ]
