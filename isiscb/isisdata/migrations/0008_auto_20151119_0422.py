# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0007_auto_20151027_1819'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='comment',
            options={'get_latest_by': 'created_on'},
        ),
        migrations.RemoveField(
            model_name='aarelation',
            name='uri',
        ),
        migrations.RemoveField(
            model_name='acrelation',
            name='uri',
        ),
        migrations.RemoveField(
            model_name='attribute',
            name='uri',
        ),
        migrations.RemoveField(
            model_name='authority',
            name='uri',
        ),
        migrations.RemoveField(
            model_name='ccrelation',
            name='uri',
        ),
        migrations.RemoveField(
            model_name='citation',
            name='uri',
        ),
        migrations.RemoveField(
            model_name='historicalacrelation',
            name='uri',
        ),
        migrations.RemoveField(
            model_name='historicalattribute',
            name='uri',
        ),
        migrations.RemoveField(
            model_name='historicalauthority',
            name='uri',
        ),
        migrations.RemoveField(
            model_name='historicalccrelation',
            name='uri',
        ),
        migrations.RemoveField(
            model_name='historicalcitation',
            name='uri',
        ),
        migrations.RemoveField(
            model_name='historicallinkeddata',
            name='uri',
        ),
        migrations.RemoveField(
            model_name='historicalperson',
            name='uri',
        ),
        migrations.RemoveField(
            model_name='historicaltracking',
            name='uri',
        ),
        migrations.RemoveField(
            model_name='linkeddata',
            name='uri',
        ),
        migrations.RemoveField(
            model_name='tracking',
            name='uri',
        ),
        migrations.AlterField(
            model_name='authority',
            name='classification_system',
            field=models.CharField(blank=True, max_length=4, null=True, help_text=b'\n    Specifies the classification system that is the source of the authority.\n    Used to group resources by the Classification system. The system used\n    currently is the Weldon System. All the other ones are for reference or\n    archival purposes only.', choices=[(b'SWP', b'SWP'), (b'NEU', b'Neu'), (b'MW', b'MW'), (b'SHOT', b'SHOT'), (b'SAC', b'SAC')]),
        ),
        migrations.AlterField(
            model_name='authority',
            name='record_status',
            field=models.CharField(blank=True, max_length=2, null=True, choices=[(b'AC', b'Active'), (b'DU', b'Duplicate'), (b'RD', b'Redirect'), (b'IN', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='classification_system',
            field=models.CharField(blank=True, max_length=4, null=True, help_text=b'\n    Specifies the classification system that is the source of the authority.\n    Used to group resources by the Classification system. The system used\n    currently is the Weldon System. All the other ones are for reference or\n    archival purposes only.', choices=[(b'SWP', b'SWP'), (b'NEU', b'Neu'), (b'MW', b'MW'), (b'SHOT', b'SHOT'), (b'SAC', b'SAC')]),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='record_status',
            field=models.CharField(blank=True, max_length=2, null=True, choices=[(b'AC', b'Active'), (b'DU', b'Duplicate'), (b'RD', b'Redirect'), (b'IN', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='classification_system',
            field=models.CharField(blank=True, max_length=4, null=True, help_text=b'\n    Specifies the classification system that is the source of the authority.\n    Used to group resources by the Classification system. The system used\n    currently is the Weldon System. All the other ones are for reference or\n    archival purposes only.', choices=[(b'SWP', b'SWP'), (b'NEU', b'Neu'), (b'MW', b'MW'), (b'SHOT', b'SHOT'), (b'SAC', b'SAC')]),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='record_status',
            field=models.CharField(blank=True, max_length=2, null=True, choices=[(b'AC', b'Active'), (b'DU', b'Duplicate'), (b'RD', b'Redirect'), (b'IN', b'Inactive')]),
        ),
        migrations.AlterField(
            model_name='historicaltracking',
            name='type_controlled',
            field=models.CharField(blank=True, max_length=2, null=True, choices=[(b'HS', b'HSTM Upload'), (b'PT', b'Printed'), (b'AU', b'Authorized'), (b'PD', b'Proofed'), (b'FU', b'Fully Entered'), (b'BD', b'Bulk Data Update')]),
        ),
        migrations.AlterField(
            model_name='tracking',
            name='type_controlled',
            field=models.CharField(blank=True, max_length=2, null=True, choices=[(b'HS', b'HSTM Upload'), (b'PT', b'Printed'), (b'AU', b'Authorized'), (b'PD', b'Proofed'), (b'FU', b'Fully Entered'), (b'BD', b'Bulk Data Update')]),
        ),
    ]
