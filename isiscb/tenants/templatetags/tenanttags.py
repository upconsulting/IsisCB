from __future__ import unicode_literals
from django import template
register = template.Library()

@register.filter
def featured_column_width(tweet_url):
    if tweet_url:
        return 8
    return 12