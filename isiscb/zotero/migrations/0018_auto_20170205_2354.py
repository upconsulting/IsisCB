# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('zotero', '0017_draftcitation_extra'),
    ]

    operations = [
        migrations.AlterField(
            model_name='importaccession',
            name='name',
            field=models.CharField(max_length=255, db_index=True),
        ),
    ]
