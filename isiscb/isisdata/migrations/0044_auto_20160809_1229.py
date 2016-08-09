# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.db.models import Q
from django.db import transaction

from isisdata.utils import normalize

import sys
from itertools import chain


def update_title_for_sort(apps, schema_editor):
    Citation = apps.get_model("isisdata", "Citation")
    CCRelation = apps.get_model("isisdata", "CCRelation")

    def get_title(obj):
        title = obj.title
        if not title:
            title_parts = []
            for relation in get_related(obj):
                if relation.type_controlled =='RO' and relation.object and relation.object.title:
                    title_parts.append(relation.object.title)
                if relation.type_controlled == 'RB' and relation.subject and relation.subject.title:
                    title_parts.append(relation.subject.title)
            return u' '.join(title_parts)
        return title

    def get_related(obj):
        query = Q(subject_id=obj.id) | Q(object_id=obj.id) & (Q(type_controlled='RO') | Q(type_controlled='RB'))
        return CCRelation.objects.filter(query)

    # qs_with_titles = Citation.objects.filter(~Q(title=u''))
    # print 'Migrating %i citations with titles' % qs_with_titles.count()
    # for i in xrange(0, qs_with_titles.count(), 5000):
    #     print '\r', i,
    #     sys.stdout.flush()
    #     with transaction.atomic():
    #         for citation in qs_with_titles[i:i+5000]:
    #             citation.title_for_sort = normalize(citation.title)
    #             citation.save()

    qs_without_titles = Citation.objects.all()
    print 'Migrating %i citations' % qs_without_titles.count()
    for i in xrange(0, qs_without_titles.count(), 5000):
        print '\r', i,
        sys.stdout.flush()
        with transaction.atomic():
            for citation in qs_without_titles[i:i+5000]:
                citation.title_for_sort = normalize(get_title(citation))
                citation.save()


def clear_title_for_sort(apps, schema_editor):
    Citation = apps.get_model("isisdata", "Citation")
    Citation.objects.all().update(title_for_sort=u'')


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0043_auto_20160809_1229'),
    ]

    operations = [
        migrations.RunPython(update_title_for_sort, clear_title_for_sort)
    ]
