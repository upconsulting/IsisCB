# Generated by Django 3.1.13 on 2022-08-11 21:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0097_citationcollection_subjects'),
    ]

    operations = [
        migrations.AddField(
            model_name='citationcollection',
            name='coverimage_url',
            field=models.URLField(blank=True),
        ),
    ]
