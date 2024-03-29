# Generated by Django 3.1.13 on 2023-03-14 01:25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('isisdata', '0116_auto_20230224_0224'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='belongs_to_tenant',
            field=models.ForeignKey(blank=True, help_text='The tenant this dataset belongs to.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='isisdata.tenant'),
        ),
        migrations.AddField(
            model_name='tenant',
            name='default_dataset',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to='isisdata.dataset'),
        ),
        migrations.AlterField(
            model_name='isiscbrole',
            name='users',
            field=models.ManyToManyField(related_name='isiscb_roles', to=settings.AUTH_USER_MODEL),
        ),
    ]
