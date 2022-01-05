# Generated by Django 3.0.7 on 2021-04-24 18:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('zotero', '0026_auto_20200601_0013'),
        ('isisdata', '0091_auto_20200601_0013'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aarelation',
            name='type_controlled',
            field=models.CharField(blank=True, choices=[('IDTO', 'Is Identical To'), ('PAOF', 'Is Parent Of'), ('ASWI', 'Is Associated With')], help_text='Controlled term specifying the nature of the relationship (the predicate between the subject and object).', max_length=5, null=True),
        ),
        migrations.CreateModel(
            name='AARSet',
            fields=[
                ('administrator_notes', models.TextField(blank=True, help_text='Curatorial discussion about the record.', null=True)),
                ('record_history', models.TextField(blank=True, help_text="Notes about the provenance of the information in this record. e.g. 'supplied by the author,' 'imported from SHOT bibliography,' 'generated by crawling UC Press website'", null=True)),
                ('modified_on', models.DateTimeField(auto_now=True, help_text='Date and time at which this object was last updated.', null=True)),
                ('public', models.BooleanField(default=True, help_text='Controls whether this instance can be viewed by end users.')),
                ('record_status_value', models.CharField(blank=True, choices=[('Active', 'Active'), ('Duplicate', 'Delete'), ('Redirect', 'Redirect'), ('Inactive', 'Inactive')], db_index=True, default='Active', max_length=255, null=True)),
                ('record_status_explanation', models.CharField(blank=True, max_length=255, null=True)),
                ('created_on_fm', models.DateTimeField(help_text='Value of CreatedOn from the original FM database.', null=True)),
                ('created_by_fm', models.CharField(blank=True, help_text='Value of CreatedBy from the original FM database.', max_length=255, null=True)),
                ('modified_on_fm', models.DateTimeField(help_text='Value of ModifiedBy from the original FM database.', null=True, verbose_name='modified on (FM)')),
                ('modified_by_fm', models.CharField(blank=True, help_text='Value of ModifiedOn from the original FM database.', max_length=255, verbose_name='modified by (FM)')),
                ('dataset_literal', models.CharField(blank=True, max_length=255, null=True)),
                ('id', models.CharField(help_text='In the format {PRE}{ZEROS}{NN}, where PRE is a three-letter prefix indicating the record type (e.g. CBA for Authority), NN is an integer, and ZEROS is 0-9 zeros to pad NN such that ZEROS+NN is nine characters in length.', max_length=200, primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, max_length=255)),
                ('description', models.TextField(blank=True)),
                ('belongs_to', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='isisdata.Dataset')),
                ('modified_by', models.ForeignKey(blank=True, help_text='The most recent user to modify this object.', null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('zotero_accession', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='zotero.ImportAccession')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AARelationType',
            fields=[
                ('administrator_notes', models.TextField(blank=True, help_text='Curatorial discussion about the record.', null=True)),
                ('record_history', models.TextField(blank=True, help_text="Notes about the provenance of the information in this record. e.g. 'supplied by the author,' 'imported from SHOT bibliography,' 'generated by crawling UC Press website'", null=True)),
                ('modified_on', models.DateTimeField(auto_now=True, help_text='Date and time at which this object was last updated.', null=True)),
                ('public', models.BooleanField(default=True, help_text='Controls whether this instance can be viewed by end users.')),
                ('record_status_value', models.CharField(blank=True, choices=[('Active', 'Active'), ('Duplicate', 'Delete'), ('Redirect', 'Redirect'), ('Inactive', 'Inactive')], db_index=True, default='Active', max_length=255, null=True)),
                ('record_status_explanation', models.CharField(blank=True, max_length=255, null=True)),
                ('created_on_fm', models.DateTimeField(help_text='Value of CreatedOn from the original FM database.', null=True)),
                ('created_by_fm', models.CharField(blank=True, help_text='Value of CreatedBy from the original FM database.', max_length=255, null=True)),
                ('modified_on_fm', models.DateTimeField(help_text='Value of ModifiedBy from the original FM database.', null=True, verbose_name='modified on (FM)')),
                ('modified_by_fm', models.CharField(blank=True, help_text='Value of ModifiedOn from the original FM database.', max_length=255, verbose_name='modified by (FM)')),
                ('dataset_literal', models.CharField(blank=True, max_length=255, null=True)),
                ('id', models.CharField(help_text='In the format {PRE}{ZEROS}{NN}, where PRE is a three-letter prefix indicating the record type (e.g. CBA for Authority), NN is an integer, and ZEROS is 0-9 zeros to pad NN such that ZEROS+NN is nine characters in length.', max_length=200, primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, max_length=255)),
                ('description', models.TextField(blank=True)),
                ('relation_type_controlled', models.CharField(blank=True, choices=[('TSTR', 'Structural'), ('TONT', 'Ontological'), ('TTEM', 'Temporal'), ('TGEO', 'Geographical')], help_text='The type of the relationship.', max_length=4, null=True)),
                ('base_type', models.CharField(blank=True, choices=[('IDTO', 'Is Identical To'), ('PAOF', 'Is Parent Of'), ('ASWI', 'Is Associated With')], help_text='The base type the new relationship type can be mapped to.', max_length=5, null=True)),
                ('aarset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='relation_types', to='isisdata.AARSet')),
                ('belongs_to', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='isisdata.Dataset')),
                ('modified_by', models.ForeignKey(blank=True, help_text='The most recent user to modify this object.', null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('zotero_accession', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='zotero.ImportAccession')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='aarelation',
            name='aar_type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='isisdata.AARelationType'),
        ),
    ]
