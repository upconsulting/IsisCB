# Generated by Django 3.0.7 on 2022-07-16 00:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0097_auto_20220715_0143'),
    ]

    operations = [
        migrations.CreateModel(
            name='TenantRule',
            fields=[
                ('accessrule_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='isisdata.AccessRule')),
                ('tenant', models.ForeignKey(blank=True, help_text='The tenant this rule allows access to.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='isisdata.Tenant')),
            ],
            bases=('isisdata.accessrule',),
        ),
    ]