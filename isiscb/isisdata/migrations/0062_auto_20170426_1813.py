# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-04-26 18:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0061_auto_20170324_1929'),
    ]

    operations = [
        migrations.AddField(
            model_name='authority',
            name='tracking_state',
            field=models.CharField(blank=True, choices=[(b'HS', b'HSTM Upload'), (b'PT', b'Printed'), (b'AU', b'Authorized'), (b'PD', b'Proofed'), (b'FU', b'Fully Entered'), (b'BD', b'Bulk Data Update')], max_length=2, null=True),
        ),
        migrations.AddField(
            model_name='citation',
            name='tracking_state',
            field=models.CharField(blank=True, choices=[(b'HS', b'HSTM Upload'), (b'PT', b'Printed'), (b'AU', b'Authorized'), (b'PD', b'Proofed'), (b'FU', b'Fully Entered'), (b'BD', b'Bulk Data Update')], max_length=2, null=True),
        ),
        migrations.AddField(
            model_name='historicalauthority',
            name='tracking_state',
            field=models.CharField(blank=True, choices=[(b'HS', b'HSTM Upload'), (b'PT', b'Printed'), (b'AU', b'Authorized'), (b'PD', b'Proofed'), (b'FU', b'Fully Entered'), (b'BD', b'Bulk Data Update')], max_length=2, null=True),
        ),
        migrations.AddField(
            model_name='historicalcitation',
            name='tracking_state',
            field=models.CharField(blank=True, choices=[(b'HS', b'HSTM Upload'), (b'PT', b'Printed'), (b'AU', b'Authorized'), (b'PD', b'Proofed'), (b'FU', b'Fully Entered'), (b'BD', b'Bulk Data Update')], max_length=2, null=True),
        ),
        migrations.AddField(
            model_name='historicalperson',
            name='tracking_state',
            field=models.CharField(blank=True, choices=[(b'HS', b'HSTM Upload'), (b'PT', b'Printed'), (b'AU', b'Authorized'), (b'PD', b'Proofed'), (b'FU', b'Fully Entered'), (b'BD', b'Bulk Data Update')], max_length=2, null=True),
        ),
        migrations.AlterField(
            model_name='authority',
            name='type_controlled',
            field=models.CharField(blank=True, choices=[(b'PE', b'Person'), (b'IN', b'Institution'), (b'TI', b'Time Period'), (b'GE', b'Geographic Term'), (b'SE', b'Serial Publication'), (b'CT', b'Classification Term'), (b'CO', b'Concept'), (b'CW', b'Creative Work'), (b'EV', b'Event'), (b'CR', b'Cross-reference')], help_text=b'Specifies authority type. Each authority thema has its own list of controlled type vocabulary.', max_length=2, null=True, verbose_name=b'type'),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='type_controlled',
            field=models.CharField(blank=True, choices=[(b'PE', b'Person'), (b'IN', b'Institution'), (b'TI', b'Time Period'), (b'GE', b'Geographic Term'), (b'SE', b'Serial Publication'), (b'CT', b'Classification Term'), (b'CO', b'Concept'), (b'CW', b'Creative Work'), (b'EV', b'Event'), (b'CR', b'Cross-reference')], help_text=b'Specifies authority type. Each authority thema has its own list of controlled type vocabulary.', max_length=2, null=True, verbose_name=b'type'),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='type_controlled',
            field=models.CharField(blank=True, choices=[(b'PE', b'Person'), (b'IN', b'Institution'), (b'TI', b'Time Period'), (b'GE', b'Geographic Term'), (b'SE', b'Serial Publication'), (b'CT', b'Classification Term'), (b'CO', b'Concept'), (b'CW', b'Creative Work'), (b'EV', b'Event'), (b'CR', b'Cross-reference')], help_text=b'Specifies authority type. Each authority thema has its own list of controlled type vocabulary.', max_length=2, null=True, verbose_name=b'type'),
        ),
    ]
