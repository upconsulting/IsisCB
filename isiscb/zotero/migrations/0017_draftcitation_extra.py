# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('zotero', '0016_draftcitation_language'),
    ]

    operations = [
        migrations.AddField(
            model_name='draftcitation',
            name='extra',
            field=models.TextField(null=True, blank=True),
        ),
    ]
