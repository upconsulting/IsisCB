# Generated by Django 3.1.13 on 2023-10-13 01:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0127_tenantsettings_public_search_all_tenants_default'),
    ]

    operations = [
        migrations.AddField(
            model_name='cachedtimeline',
            name='owning_tenant',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
