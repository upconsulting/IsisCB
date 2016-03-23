# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('openurl', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='resolver',
            name='link_icon',
            field=models.URLField(help_text=b'Location of an image that will be rendered as a link next to search results.', max_length=1000, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='resolver',
            name='link_text',
            field=models.CharField(help_text=b'Text that will be rendered as a link next to search results if ``link_icon`` is not available.', max_length=1000, null=True, blank=True),
        ),
    ]
