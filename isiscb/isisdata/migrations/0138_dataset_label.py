# Generated by Django 3.1.13 on 2024-09-08 20:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0137_tenant_default_datasets_reading'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='label',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
