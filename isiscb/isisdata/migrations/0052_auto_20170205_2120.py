# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0051_auto_20170114_2231'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasetrule',
            name='dataset',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='bio_markup_type',
            field=models.CharField(default=b'markdown', max_length=30, editable=False, choices=[(b'', b'--'), (b'html', 'HTML'), (b'plain', 'Plain'), (b'markdown', 'Markdown')]),
        ),
    ]
