# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0032_auto_20160629_1641'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='bio_markup_type',
            field=models.CharField(default=b'markdown', max_length=30, editable=False, choices=[(b'', b'--'), (b'markdown', b'markdown')]),
        ),
    ]
