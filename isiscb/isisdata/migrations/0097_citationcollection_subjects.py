# Generated by Django 3.1.13 on 2022-08-11 21:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0096_featuredauthority_googlebooksdata_wikipediadata'),
    ]

    operations = [
        migrations.AddField(
            model_name='citationcollection',
            name='subjects',
            field=models.ManyToManyField(to='isisdata.Authority'),
        ),
    ]