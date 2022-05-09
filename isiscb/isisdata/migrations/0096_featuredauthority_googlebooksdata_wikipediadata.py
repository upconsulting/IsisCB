# Generated by Django 3.1.13 on 2022-05-03 02:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0095_auto_20210826_0119'),
    ]

    operations = [
        migrations.CreateModel(
            name='FeaturedAuthority',
            fields=[
                ('authority', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='isisdata.authority')),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='GoogleBooksData',
            fields=[
                ('citation', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='isisdata.citation')),
                ('image_url', models.TextField()),
                ('image_size', models.CharField(blank=True, max_length=255)),
                ('last_modified', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='WikipediaData',
            fields=[
                ('authority', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='isisdata.authority')),
                ('img_url', models.URLField(max_length=255)),
                ('intro', models.TextField(blank=True, null=True)),
                ('credit', models.URLField(max_length=255)),
                ('last_modified', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
