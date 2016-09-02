# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0048_citationcollection_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='authority',
            name='classification_system',
            field=models.CharField(default=b'SPWC', choices=[(b'SPWT', b'Weldon Thesaurus Terms (2002-present)'), (b'SPWC', b'Weldon Classification System (2002-present)'), (b'GUE', b'Guerlac Committee Classification System (1953-2001)'), (b'NEU', b'Neu'), (b'MW', b'MW'), (b'SHOT', b'SHOT'), (b'SAC', b'SAC'), (b'PN', b'Proper name')], max_length=4, blank=True, help_text=b'Specifies the classification system that is the source of the authority. Used to group resources by the Classification system. The system used currently is the Weldon System. All the other ones are for reference or archival purposes only.', null=True),
        ),
        migrations.AlterField(
            model_name='citationcollection',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='classification_system',
            field=models.CharField(default=b'SPWC', choices=[(b'SPWT', b'Weldon Thesaurus Terms (2002-present)'), (b'SPWC', b'Weldon Classification System (2002-present)'), (b'GUE', b'Guerlac Committee Classification System (1953-2001)'), (b'NEU', b'Neu'), (b'MW', b'MW'), (b'SHOT', b'SHOT'), (b'SAC', b'SAC'), (b'PN', b'Proper name')], max_length=4, blank=True, help_text=b'Specifies the classification system that is the source of the authority. Used to group resources by the Classification system. The system used currently is the Weldon System. All the other ones are for reference or archival purposes only.', null=True),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='classification_system',
            field=models.CharField(default=b'SPWC', choices=[(b'SPWT', b'Weldon Thesaurus Terms (2002-present)'), (b'SPWC', b'Weldon Classification System (2002-present)'), (b'GUE', b'Guerlac Committee Classification System (1953-2001)'), (b'NEU', b'Neu'), (b'MW', b'MW'), (b'SHOT', b'SHOT'), (b'SAC', b'SAC'), (b'PN', b'Proper name')], max_length=4, blank=True, help_text=b'Specifies the classification system that is the source of the authority. Used to group resources by the Classification system. The system used currently is the Weldon System. All the other ones are for reference or archival purposes only.', null=True),
        ),
    ]
