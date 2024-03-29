# Generated by Django 3.1.13 on 2023-06-05 00:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0123_auto_20230430_2100'),
    ]

    operations = [
        migrations.AlterField(
            model_name='authority',
            name='classification_code',
            field=models.CharField(blank=True, db_index=True, help_text='alphanumeric code used in previous classification systems to describe Category Divisions. Primarily of historical interest only. Used primarily for Codes for the classificationTerms. however, can be used for other kinds of terms as appropriate.', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='authority',
            name='classification_hierarchy',
            field=models.CharField(blank=True, db_index=True, help_text='Used for Category Divisions to describe where they fall in the hierarchy.', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='authority',
            name='description',
            field=models.TextField(blank=True, help_text="A brief description that will be displayed to help identify the authority. Such as, brief bio or a scope note. For Category Division will be text like 'Category Division from the XXX classification schema.'", null=True),
        ),
        migrations.AlterField(
            model_name='authority',
            name='type_controlled',
            field=models.CharField(blank=True, choices=[('PE', 'Person'), ('IN', 'Institution'), ('TI', 'Time Period'), ('GE', 'Geographic Term'), ('SE', 'Serial Publication'), ('CT', 'Category Division'), ('CO', 'Concept'), ('CW', 'Creative Work'), ('EV', 'Event'), ('CR', 'Cross-reference'), ('BL', 'Bibliographic List')], db_index=True, help_text='Specifies authority type. Each authority thema has its own list of controlled type vocabulary.', max_length=2, null=True, verbose_name='type'),
        ),
        migrations.AlterField(
            model_name='citationsubtype',
            name='description',
            field=models.TextField(blank=True, help_text="A brief description that will be displayed to help identify the authority. Such as, brief bio or a scope note. For Category Division will be text like 'Category Division from the XXX classification schema.'", null=True),
        ),
        migrations.AlterField(
            model_name='classificationsystem',
            name='is_default',
            field=models.BooleanField(default=False, help_text='Marks a classification system as the default for authorities that are not assigned another system.'),
        ),
        migrations.AlterField(
            model_name='classificationsystem',
            name='owning_tenant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_classification_systems', to='isisdata.tenant'),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='classification_code',
            field=models.CharField(blank=True, db_index=True, help_text='alphanumeric code used in previous classification systems to describe Category Divisions. Primarily of historical interest only. Used primarily for Codes for the classificationTerms. however, can be used for other kinds of terms as appropriate.', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='classification_hierarchy',
            field=models.CharField(blank=True, db_index=True, help_text='Used for Category Divisions to describe where they fall in the hierarchy.', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='description',
            field=models.TextField(blank=True, help_text="A brief description that will be displayed to help identify the authority. Such as, brief bio or a scope note. For Category Division will be text like 'Category Division from the XXX classification schema.'", null=True),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='type_controlled',
            field=models.CharField(blank=True, choices=[('PE', 'Person'), ('IN', 'Institution'), ('TI', 'Time Period'), ('GE', 'Geographic Term'), ('SE', 'Serial Publication'), ('CT', 'Category Division'), ('CO', 'Concept'), ('CW', 'Creative Work'), ('EV', 'Event'), ('CR', 'Cross-reference'), ('BL', 'Bibliographic List')], db_index=True, help_text='Specifies authority type. Each authority thema has its own list of controlled type vocabulary.', max_length=2, null=True, verbose_name='type'),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='classification_code',
            field=models.CharField(blank=True, db_index=True, help_text='alphanumeric code used in previous classification systems to describe Category Divisions. Primarily of historical interest only. Used primarily for Codes for the classificationTerms. however, can be used for other kinds of terms as appropriate.', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='classification_hierarchy',
            field=models.CharField(blank=True, db_index=True, help_text='Used for Category Divisions to describe where they fall in the hierarchy.', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='description',
            field=models.TextField(blank=True, help_text="A brief description that will be displayed to help identify the authority. Such as, brief bio or a scope note. For Category Division will be text like 'Category Division from the XXX classification schema.'", null=True),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='type_controlled',
            field=models.CharField(blank=True, choices=[('PE', 'Person'), ('IN', 'Institution'), ('TI', 'Time Period'), ('GE', 'Geographic Term'), ('SE', 'Serial Publication'), ('CT', 'Category Division'), ('CO', 'Concept'), ('CW', 'Creative Work'), ('EV', 'Event'), ('CR', 'Cross-reference'), ('BL', 'Bibliographic List')], db_index=True, help_text='Specifies authority type. Each authority thema has its own list of controlled type vocabulary.', max_length=2, null=True, verbose_name='type'),
        ),
        migrations.AlterField(
            model_name='tenantimage',
            name='image_type',
            field=models.CharField(blank=True, choices=[('DAU', 'Authority Default Image Author'), ('DPE', 'Authority Default Image Person'), ('DCO', 'Authority Default Image Concept'), ('DIN', 'Authority Default Image Institution'), ('DGE', 'Authority Default Image Geographic Term'), ('DPU', 'Authority Default Image Publisher'), ('DTI', 'Authority Default Image Timeperiod'), ('DCL', 'Authority Default Image Category Division'), ('AB', 'About page image')], db_index=True, default='AB', max_length=255, null=True),
        ),
    ]
