# Generated by Django 3.1.13 on 2023-03-27 01:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0117_auto_20230314_0125'),
        ('zotero', '0026_auto_20200601_0013'),
    ]

    operations = [
        migrations.AddField(
            model_name='importaccession',
            name='tenant',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='isisdata.tenant'),
        ),
    ]
