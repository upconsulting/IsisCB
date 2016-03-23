from django.db import models
from django.contrib.auth.models import User

import re


def help_text(s):
    """
    Cleans up help strings so that we can write them in ways that are
    human-readable without screwing up formatting in the admin interface.
    """
    return re.sub('\s+', ' ', s).strip()


class CuratedMixin(models.Model):
    added_by = models.ForeignKey(User)
    added_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Institution(CuratedMixin):
    """
    Represents an institution with which a user can be affiliated.
    """

    name = models.CharField(max_length=255)
    notes = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return self.name


class Resolver(CuratedMixin):
    """
    An OpenURL resolver.
    """

    belongs_to = models.OneToOneField('Institution', related_name='resolver')
    endpoint = models.URLField(max_length=1000, help_text=help_text("""
    The address to which CoINS metadata will be appended to create an OpenURL
    link."""))
    notes = models.TextField(null=True, blank=True)

    link_icon = models.URLField(max_length=1000, blank=True, null=True,
                                help_text=help_text("""
    Location of an image that will be rendered as a link next to search results.
    """))
    link_text = models.CharField(max_length=1000, blank=True, null=True,
                                 help_text=help_text("""
    Text that will be rendered as a link next to search results if
    ``link_icon`` is not available."""))

    def __unicode__(self):
        return self.belongs_to.name
