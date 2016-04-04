# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import markupfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0012_add_user_profiles'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='_bio_rendered',
            field=models.TextField(null=True, editable=False),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='bio_markup_type',
            field=models.CharField(default=b'markdown', max_length=30, editable=False, choices=[(b'', b'--'), (b'markdown', b'markdown')]),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='bio',
            field=markupfield.fields.MarkupField(null=True, rendered_field=True, blank=True),
        ),
    ]
