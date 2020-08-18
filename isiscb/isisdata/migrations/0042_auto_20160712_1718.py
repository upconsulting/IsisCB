# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('zotero', '0011_importaccession_processed'),
        ('isisdata', '0041_auto_20160712_1656'),
    ]

    operations = [
        migrations.AddField(
            model_name='aarelation',
            name='zotero_accession',
            field=models.ForeignKey(blank=True, to='zotero.ImportAccession', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='acrelation',
            name='zotero_accession',
            field=models.ForeignKey(blank=True, to='zotero.ImportAccession', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='attribute',
            name='zotero_accession',
            field=models.ForeignKey(blank=True, to='zotero.ImportAccession', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='authority',
            name='zotero_accession',
            field=models.ForeignKey(blank=True, to='zotero.ImportAccession', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='ccrelation',
            name='zotero_accession',
            field=models.ForeignKey(blank=True, to='zotero.ImportAccession', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='citation',
            name='zotero_accession',
            field=models.ForeignKey(blank=True, to='zotero.ImportAccession', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='dataset',
            name='zotero_accession',
            field=models.ForeignKey(blank=True, to='zotero.ImportAccession', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='historicalacrelation',
            name='zotero_accession',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='zotero.ImportAccession', null=True),
        ),
        migrations.AddField(
            model_name='historicalattribute',
            name='zotero_accession',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='zotero.ImportAccession', null=True),
        ),
        migrations.AddField(
            model_name='historicalauthority',
            name='zotero_accession',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='zotero.ImportAccession', null=True),
        ),
        migrations.AddField(
            model_name='historicalccrelation',
            name='zotero_accession',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='zotero.ImportAccession', null=True),
        ),
        migrations.AddField(
            model_name='historicalcitation',
            name='zotero_accession',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='zotero.ImportAccession', null=True),
        ),
        migrations.AddField(
            model_name='historicallinkeddata',
            name='zotero_accession',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='zotero.ImportAccession', null=True),
        ),
        migrations.AddField(
            model_name='historicalperson',
            name='zotero_accession',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='zotero.ImportAccession', null=True),
        ),
        migrations.AddField(
            model_name='historicaltracking',
            name='zotero_accession',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.DO_NOTHING, db_constraint=False, blank=True, to='zotero.ImportAccession', null=True),
        ),
        migrations.AddField(
            model_name='linkeddata',
            name='zotero_accession',
            field=models.ForeignKey(blank=True, to='zotero.ImportAccession', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='tracking',
            name='zotero_accession',
            field=models.ForeignKey(blank=True, to='zotero.ImportAccession', null=True, on_delete=models.CASCADE),
        ),
    ]
