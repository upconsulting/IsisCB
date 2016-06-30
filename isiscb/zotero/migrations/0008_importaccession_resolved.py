# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('zotero', '0007_draftccrelation'),
    ]

    operations = [
        migrations.AddField(
            model_name='importaccession',
            name='resolved',
            field=models.BooleanField(default=False),
        ),
    ]
