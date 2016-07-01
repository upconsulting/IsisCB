# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0038_auto_20160701_1552'),
    ]

    operations = [
        migrations.CreateModel(
            name='ZoteroRule',
            fields=[
                ('accessrule_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='isisdata.AccessRule')),
            ],
            bases=('isisdata.accessrule',),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='bio_markup_type',
            field=models.CharField(default=b'markdown', max_length=30, editable=False, choices=[(b'', b'--'), (b'html', 'HTML'), (b'plain', 'Plain'), (b'markdown', 'Markdown')]),
        ),
    ]
