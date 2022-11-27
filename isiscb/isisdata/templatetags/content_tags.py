from django import template
from isisdata.models import *
import markdown as m

register = template.Library()

@register.filter
def markdown(text):
    return m.markdown(text)

@register.filter
def divide(a, b):
    return a//b
