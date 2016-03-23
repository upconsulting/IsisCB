# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Institution',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('added_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('notes', models.TextField(null=True, blank=True)),
                ('added_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Resolver',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('added_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('endpoint', models.URLField(help_text=b'The address to which CoINS metadata will be appended to create an OpenURL link.', max_length=1000)),
                ('notes', models.TextField(null=True, blank=True)),
                ('added_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('belongs_to', models.OneToOneField(related_name='resolver', to='openurl.Institution')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
