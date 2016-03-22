# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0010_userprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='authority_record',
            field=models.OneToOneField(related_name='associated_user', null=True, blank=True, to='isisdata.Authority', help_text=b"A user can 'claim' an Authority record, asserting that the record refers to theirself."),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='resolver_institution',
            field=models.ForeignKey(related_name='users', blank=True, to='openurl.Institution', help_text=b'A user can select an institution for which OpenURL links should be generated while searching.', null=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='share_email',
            field=models.BooleanField(default=False, help_text=b'A user can indicate whether or not their email address should be made public.'),
        ),
    ]
