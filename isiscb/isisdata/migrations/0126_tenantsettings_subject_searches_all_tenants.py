# Generated by Django 3.1.13 on 2023-07-02 14:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0125_auto_20230611_2012'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenantsettings',
            name='subject_searches_all_tenants',
            field=models.BooleanField(default=False),
        ),
    ]
