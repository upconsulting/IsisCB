# Generated by Django 3.1.12 on 2022-01-07 17:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0096_googlebooksdata'),
    ]

    operations = [
        migrations.AlterField(
            model_name='googlebooksdata',
            name='image_url',
            field=models.TextField(),
        ),
    ]