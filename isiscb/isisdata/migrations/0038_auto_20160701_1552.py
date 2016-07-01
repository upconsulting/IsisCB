# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

import re


def migrate_dataset_editor(apps, schema_editor):
    Dataset = apps.get_model("isisdata", "Dataset")
    for dataset in Dataset.objects.all():

        match = re.search('([^(]+)[(](.+)[)]', dataset.name)
        if match:
            dataset.editor = match.groups()[1]
            dataset.save()


def migrate_dataset_editor_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0037_dataset_editor'),
    ]

    operations = [
        migrations.RunPython(
            migrate_dataset_editor,
            migrate_dataset_editor_reverse
        )
    ]
