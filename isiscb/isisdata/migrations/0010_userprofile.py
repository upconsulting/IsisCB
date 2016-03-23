# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('openurl', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('isisdata', '0009_auto_20160208_1740'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('affiliation', models.CharField(max_length=255, null=True, blank=True)),
                ('location', models.CharField(max_length=255, null=True, blank=True)),
                ('bio', models.TextField(null=True, blank=True)),
                ('share_email', models.BooleanField(default=False)),
                ('resolver_institution', models.ForeignKey(related_name='users', blank=True, to='openurl.Institution', null=True)),
                ('user', models.OneToOneField(related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
