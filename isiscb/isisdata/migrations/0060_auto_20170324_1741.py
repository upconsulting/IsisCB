# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-24 17:41
from __future__ import unicode_literals

from django.db import migrations
from django.db.models import F
import sys

def set_citation(apps, schema_editor):
    from random import randint
    Tracking = apps.get_model("isisdata", "Tracking")
    AuthorityTracking = apps.get_model("isisdata", "AuthorityTracking")
    ContentType = apps.get_model("contenttypes", "ContentType")
    citation_type = ContentType.objects.get_by_natural_key("isisdata", "citation")
    authority_type = ContentType.objects.get_by_natural_key("isisdata", "authority")
    Tracking.objects.filter(subject_content_type=citation_type).update(citation_id=F('subject_instance_id'))

    authority_tracking = []
    for tracking in Tracking.objects.filter(subject_content_type=authority_type):
        print '\rauthority tracking', tracking.id,
        sys.stdout.flush()
        while True:
            pk = '{0}{1}'.format("TRA", "%09d" % randint(0, 999999999))
            if AuthorityTracking.objects.filter(id=pk).count() == 0:
                break

        authority_tracking.append(AuthorityTracking(
            id=pk,
            administrator_notes = tracking.administrator_notes,
            record_history = tracking.record_history,
            modified_on = tracking.modified_on,
            modified_by = tracking.modified_by,
            public = tracking.public,
            record_status_value = tracking.record_status_value,
            record_status_explanation = tracking.record_status_explanation,
            tracking_info = tracking.tracking_info,
            type_controlled = tracking.type_controlled,
            notes = tracking.notes,
            authority_id  = tracking.subject_instance_id,
        ))
    AuthorityTracking.objects.bulk_create(authority_tracking)
    Tracking.objects.filter(subject_content_type=authority_type).delete()


def clear_citation(apps, schema_editor):
    pass
    # Tracking = apps.get_model("isisdata", "Tracking")
    # Tracking.objects.all().update(citation_id=None)
    #
    # AuthorityTracking = apps.get_model("isisdata", "AuthorityTracking")
    # Tracking.objects.all().update(authority_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0059_authoritytracking_historicalauthoritytracking'),
    ]

    operations = [
        migrations.RunPython(set_citation, clear_citation)
    ]