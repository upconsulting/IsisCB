# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0042_auto_20160712_1718'),
    ]

    operations = [
        migrations.AddField(
            model_name='citation',
            name='title_for_sort',
            field=models.CharField(max_length=2000, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='historicalcitation',
            name='title_for_sort',
            field=models.CharField(max_length=2000, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='authority',
            name='classification_system',
            field=models.CharField(default=b'SWP', choices=[(b'SWP', b'SPW'), (b'NEU', b'Neu'), (b'MW', b'MW'), (b'SHOT', b'SHOT'), (b'SAC', b'SAC')], max_length=4, blank=True, help_text=b'Specifies the classification system that is the source of the authority. Used to group resources by the Classification system. The system used currently is the Weldon System. All the other ones are for reference or archival purposes only.', null=True),
        ),
        migrations.AlterField(
            model_name='citation',
            name='title',
            field=models.CharField(help_text=b"The name to be used to identify the resource. For reviews that traditionally have no title, this should be added as something like '[Review of Title (Year) by Author]'.", max_length=2000, blank=True),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='classification_system',
            field=models.CharField(default=b'SWP', choices=[(b'SWP', b'SPW'), (b'NEU', b'Neu'), (b'MW', b'MW'), (b'SHOT', b'SHOT'), (b'SAC', b'SAC')], max_length=4, blank=True, help_text=b'Specifies the classification system that is the source of the authority. Used to group resources by the Classification system. The system used currently is the Weldon System. All the other ones are for reference or archival purposes only.', null=True),
        ),
        migrations.AlterField(
            model_name='historicalcitation',
            name='title',
            field=models.CharField(help_text=b"The name to be used to identify the resource. For reviews that traditionally have no title, this should be added as something like '[Review of Title (Year) by Author]'.", max_length=2000, blank=True),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='classification_system',
            field=models.CharField(default=b'SWP', choices=[(b'SWP', b'SPW'), (b'NEU', b'Neu'), (b'MW', b'MW'), (b'SHOT', b'SHOT'), (b'SAC', b'SAC')], max_length=4, blank=True, help_text=b'Specifies the classification system that is the source of the authority. Used to group resources by the Classification system. The system used currently is the Weldon System. All the other ones are for reference or archival purposes only.', null=True),
        ),
    ]
