# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0034_auto_20160701_1453'),
    ]

    operations = [
        migrations.AddField(
            model_name='aarelation',
            name='belongs_to',
            field=models.ForeignKey(to='isisdata.Dataset', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='acrelation',
            name='belongs_to',
            field=models.ForeignKey(to='isisdata.Dataset', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='attribute',
            name='belongs_to',
            field=models.ForeignKey(to='isisdata.Dataset', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='authority',
            name='belongs_to',
            field=models.ForeignKey(to='isisdata.Dataset', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='ccrelation',
            name='belongs_to',
            field=models.ForeignKey(to='isisdata.Dataset', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='citation',
            name='belongs_to',
            field=models.ForeignKey(to='isisdata.Dataset', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='dataset',
            name='belongs_to',
            field=models.ForeignKey(to='isisdata.Dataset', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='historicalacrelation',
            name='belongs_to',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='isisdata.Dataset', null=True),
        ),
        migrations.AddField(
            model_name='historicalattribute',
            name='belongs_to',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='isisdata.Dataset', null=True),
        ),
        migrations.AddField(
            model_name='historicalauthority',
            name='belongs_to',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='isisdata.Dataset', null=True),
        ),
        migrations.AddField(
            model_name='historicalccrelation',
            name='belongs_to',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='isisdata.Dataset', null=True),
        ),
        migrations.AddField(
            model_name='historicalcitation',
            name='belongs_to',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='isisdata.Dataset', null=True),
        ),
        migrations.AddField(
            model_name='historicallinkeddata',
            name='belongs_to',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='isisdata.Dataset', null=True),
        ),
        migrations.AddField(
            model_name='historicalperson',
            name='belongs_to',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='isisdata.Dataset', null=True),
        ),
        migrations.AddField(
            model_name='historicaltracking',
            name='belongs_to',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='isisdata.Dataset', null=True),
        ),
        migrations.AddField(
            model_name='linkeddata',
            name='belongs_to',
            field=models.ForeignKey(to='isisdata.Dataset', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='tracking',
            name='belongs_to',
            field=models.ForeignKey(to='isisdata.Dataset', null=True, on_delete=models.CASCADE),
        ),
    ]
