# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('isisdata', '0004_auto_20151025_2110'),
    ]

    operations = [
        migrations.CreateModel(
            name='SearchQuery',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('parameters', models.CharField(max_length=500)),
                ('search_models', models.CharField(max_length=500, null=True, blank=True)),
                ('selected_facets', models.CharField(max_length=500, null=True, blank=True)),
                ('name', models.CharField(help_text=b'\n    Provide a memorable name so that you can find this search later.', max_length=255, null=True, blank=True)),
                ('saved', models.BooleanField(default=False)),
                ('user', models.ForeignKey(related_name='searches', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
