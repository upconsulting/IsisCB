# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('isisdata', '0046_populate_authority_name_for_sort'),
    ]

    operations = [
        migrations.CreateModel(
            name='CitationCollection',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('description', models.TextField()),
                ('citations', models.ManyToManyField(related_name='in_collections', to='isisdata.Citation')),
                ('createdBy', models.ForeignKey(related_name='citation_collections', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
        ),
        migrations.AlterField(
            model_name='authority',
            name='classification_system',
            field=models.CharField(default=b'SWP', choices=[(b'SWP', b'SPW'), (b'NEU', b'Neu'), (b'MW', b'MW'), (b'SHOT', b'SHOT'), (b'SAC', b'SAC'), (b'PN', b'Proper name')], max_length=4, blank=True, help_text=b'Specifies the classification system that is the source of the authority. Used to group resources by the Classification system. The system used currently is the Weldon System. All the other ones are for reference or archival purposes only.', null=True),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='classification_system',
            field=models.CharField(default=b'SWP', choices=[(b'SWP', b'SPW'), (b'NEU', b'Neu'), (b'MW', b'MW'), (b'SHOT', b'SHOT'), (b'SAC', b'SAC'), (b'PN', b'Proper name')], max_length=4, blank=True, help_text=b'Specifies the classification system that is the source of the authority. Used to group resources by the Classification system. The system used currently is the Weldon System. All the other ones are for reference or archival purposes only.', null=True),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='classification_system',
            field=models.CharField(default=b'SWP', choices=[(b'SWP', b'SPW'), (b'NEU', b'Neu'), (b'MW', b'MW'), (b'SHOT', b'SHOT'), (b'SAC', b'SAC'), (b'PN', b'Proper name')], max_length=4, blank=True, help_text=b'Specifies the classification system that is the source of the authority. Used to group resources by the Classification system. The system used currently is the Weldon System. All the other ones are for reference or archival purposes only.', null=True),
        ),
    ]
