# Generated by Django 3.1.13 on 2023-02-19 02:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0114_auto_20230212_2212'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenantsettings',
            name='twitter_user_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]