# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def add_profile_for_users(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("isisdata", "UserProfile")

    for user in User.objects.all():
        try:
            user.profile    # Raises RelatedObjectDoesNotExist if non-existant.
        except:
            profile = UserProfile(user=user)
            profile.save()

def remove_profile_for_users(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0011_auto_20160322_1844'),
    ]

    operations = [

        migrations.RunPython(
            add_profile_for_users,
            remove_profile_for_users
        ),
    ]
