# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='attributetype',
            name='display_name',
            field=models.CharField(help_text=b'\n    The "name" attribute is not always suitable for display in public views.\n    This field provides the name to be displayed to users.', max_length=255, null=True, blank=True),
        ),
    ]
