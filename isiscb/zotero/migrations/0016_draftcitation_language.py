# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0050_auto_20161024_1447'),
        ('zotero', '0015_draftcitation_source_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='draftcitation',
            name='language',
            field=models.ForeignKey(blank=True, to='isisdata.Language', null=True, on_delete=models.CASCADE),
        ),
    ]
