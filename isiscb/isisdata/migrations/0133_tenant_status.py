# Generated by Django 3.1.13 on 2023-12-13 01:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0132_auto_20231118_0157'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant',
            name='status',
            field=models.CharField(choices=[('ACT', 'Active'), ('IAC', 'Inactive')], db_index=True, default='ACT', help_text='\n             Mark a tenant as active to include it in the searches of other tenants when \n             "all projects" are searched, and in the seachbar on the user profile pages.\n             ', max_length=4),
        ),
    ]
