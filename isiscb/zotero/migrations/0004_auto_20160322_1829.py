# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('zotero', '0003_auto_20160218_1614'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='draftauthority',
            options={'verbose_name': 'draft authority record', 'verbose_name_plural': 'draft authority records'},
        ),
        migrations.AlterField(
            model_name='draftacrelation',
            name='type_controlled',
            field=models.CharField(max_length=2, choices=[('AU', 'Author'), ('ED', 'Editor'), ('AD', 'Advisor'), ('CO', 'Contributor'), ('TR', 'Translator'), ('SU', 'Subject'), ('CA', 'Category'), ('PU', 'Publisher'), ('SC', 'School'), ('IN', 'Institution'), ('ME', 'Meeting'), ('PE', 'Periodical'), ('BS', 'Book Series')]),
        ),
        migrations.AlterField(
            model_name='draftauthority',
            name='type_controlled',
            field=models.CharField(blank=True, max_length=2, null=True, choices=[('PE', 'Person'), ('IN', 'Institution'), ('TI', 'Time Period'), ('GE', 'Geographic Term'), ('SE', 'Serial Publication'), ('CT', 'Classification Term'), ('CO', 'Concept'), ('CW', 'Creative Work'), ('EV', 'Event'), ('CR', 'Cross-reference'), ('PU', 'Publisher')]),
        ),
        migrations.AlterField(
            model_name='draftcitation',
            name='type_controlled',
            field=models.CharField(blank=True, max_length=2, null=True, choices=[('BO', 'Book'), ('AR', 'Article'), ('CH', 'Chapter'), ('RE', 'Review'), ('ES', 'Essay Review'), ('TH', 'Thesis'), ('EV', 'Event'), ('PR', 'Presentation'), ('IN', 'Interactive Resource'), ('WE', 'Website'), ('AP', 'Application')]),
        ),
    ]
