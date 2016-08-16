# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('zotero', '0011_importaccession_processed'),
    ]

    operations = [
        migrations.AddField(
            model_name='draftauthority',
            name='name_for_sort',
            field=models.CharField(max_length=2000, null=True, blank=True),
        ),
    ]
