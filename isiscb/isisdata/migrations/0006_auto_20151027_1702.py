# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0005_searchquery'),
    ]

    operations = [
        migrations.AddField(
            model_name='citation',
            name='publication_date',
            field=models.DateField(help_text=b'\n    Used for search and sort functionality. Does not replace Attribute\n    functionality.', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='historicalcitation',
            name='publication_date',
            field=models.DateField(help_text=b'\n    Used for search and sort functionality. Does not replace Attribute\n    functionality.', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='value',
            name='attribute',
            field=models.OneToOneField(related_name='value', to='isisdata.Attribute', help_text=b'\n    The Attribute to which this Value belongs.'),
        ),
    ]
