# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0053_auto_20170205_2125'),
    ]

    operations = [
        migrations.AlterField(
            model_name='authority',
            name='classification_code',
            field=models.CharField(help_text=b'alphanumeric code used in previous classification systems to describe classification terms. Primarily of historical interest only. Used primarily for Codes for the classificationTerms. however, can be used for other kinds of terms as appropriate.', max_length=255, null=True, db_index=True, blank=True),
        ),
        migrations.AlterField(
            model_name='authority',
            name='classification_hierarchy',
            field=models.CharField(help_text=b'Used for Classification Terms to describe where they fall in the hierarchy.', max_length=255, null=True, db_index=True, blank=True),
        ),
        migrations.AlterField(
            model_name='datasetrule',
            name='dataset',
            field=models.CharField(default=None, max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='classification_code',
            field=models.CharField(help_text=b'alphanumeric code used in previous classification systems to describe classification terms. Primarily of historical interest only. Used primarily for Codes for the classificationTerms. however, can be used for other kinds of terms as appropriate.', max_length=255, null=True, db_index=True, blank=True),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='classification_hierarchy',
            field=models.CharField(help_text=b'Used for Classification Terms to describe where they fall in the hierarchy.', max_length=255, null=True, db_index=True, blank=True),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='classification_code',
            field=models.CharField(help_text=b'alphanumeric code used in previous classification systems to describe classification terms. Primarily of historical interest only. Used primarily for Codes for the classificationTerms. however, can be used for other kinds of terms as appropriate.', max_length=255, null=True, db_index=True, blank=True),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='classification_hierarchy',
            field=models.CharField(help_text=b'Used for Classification Terms to describe where they fall in the hierarchy.', max_length=255, null=True, db_index=True, blank=True),
        ),
    ]
