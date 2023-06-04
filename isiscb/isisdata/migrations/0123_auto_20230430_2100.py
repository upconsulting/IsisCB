# Generated by Django 3.1.13 on 2023-04-30 21:00

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0122_auto_20230430_2050'),
    ]

    operations = [
        migrations.AddField(
            model_name='classificationsystem',
            name='available_to_all',
            field=models.BooleanField(default=False, help_text='Marks a classification system as available to all tenants.'),
        ),
        migrations.AddField(
            model_name='classificationsystem',
            name='default_for',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=2, null=True), blank=True, null=True, size=None),
        ),
    ]
