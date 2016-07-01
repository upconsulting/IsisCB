# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

import re
from itertools import chain


def migrate_dataset(apps, schema_editor):
    Citation = apps.get_model("isisdata", "Citation")
    Authority = apps.get_model("isisdata", "Authority")
    Dataset = apps.get_model("isisdata", "Dataset")

    datasets = {}
    dataset_literals = Citation.objects.all().distinct('dataset_literal').values_list('dataset_literal', flat=True)
    for literal in dataset_literals:
        if not literal:
            continue
        match = re.search('([^(]+)[(](.+)[)]', literal)
        if match:
            datasetname, editorname  = match.groups()
            dataset, _ = Dataset.objects.get_or_create(name=datasetname)
            subdataset, _ = Dataset.objects.get_or_create(name=literal,
                                                          defaults={'belongs_to': dataset})
            datasets[literal] = subdataset
        else:
            dataset, _ = Dataset.objects.get_or_create(name=literal)
            datasets[literal] = dataset

    for literal in dataset_literals:
        if not literal:
            continue
        Citation.objects.filter(dataset_literal=literal).update(belongs_to=datasets[literal])


def migration_dataset_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0035_auto_20160701_1457'),
    ]

    operations = [
        migrations.RunPython(
            migrate_dataset,
            migration_dataset_reverse
        ),
    ]
