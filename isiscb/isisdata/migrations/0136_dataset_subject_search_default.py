# Generated by Django 3.1.13 on 2024-04-14 15:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0135_tenant_blog_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='subject_search_default',
            field=models.BooleanField(default=True),
        ),
    ]
