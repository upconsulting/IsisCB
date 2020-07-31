# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function

from builtins import range
from django.db import models, migrations
from django.db.models import Q
from django.db import transaction

from isisdata.utils import normalize
from unidecode import unidecode

import sys
from itertools import chain


def update_name_for_sort(apps, schema_editor):
    Authority = apps.get_model("zotero", "DraftAuthority")

    # If we don't order by ID, the queryset will shift on every inner iteration.
    qs = Authority.objects.all().order_by('id')
    N = qs.count()
    CHUNK = 500
    print('Migrating %i authority records' % N)
    for i in range(0, N + 1, CHUNK):
        print('\r', i, end=' ')
        sys.stdout.flush()
        with transaction.atomic():
            # -vv- The database read is here. -vv-
            for authority in qs[i:i+CHUNK]:
                authority.name_for_sort = normalize(unidecode(authority.name))
                authority.save()


def clear_name_for_sort(apps, schema_editor):
    DraftAuthority = apps.get_model("zotero", "DraftAuthority")
    DraftAuthority.objects.all().update(name_for_sort=u'')


class Migration(migrations.Migration):

    dependencies = [
        ('zotero', '0012_draftauthority_name_for_sort'),
    ]

    operations = [
        migrations.RunPython(update_name_for_sort, clear_name_for_sort)
    ]
