from django import template
from isisdata.models import *
import markdown as m
from io import StringIO

def unmark_element(element, stream=None):
    if stream is None:
        stream = StringIO()
    if element.text:
        stream.write(element.text)
    for sub in element:
        unmark_element(sub, stream)
    if element.tail:
        stream.write(element.tail)
    return stream.getvalue()

# patching Markdown
m.Markdown.output_formats["plain"] = unmark_element
__md = m.Markdown(output_format="plain")
__md.stripTopLevelTags = False

def unmark(text):
    return __md.convert(text)

register = template.Library()

@register.filter
def markdown(text):
    return m.markdown(text)

@register.filter
def markdown_snippet(text, nr_of_words):
    raw_text = unmark(text)
    words = raw_text.split(" ")
    if len(words) < nr_of_words:
        return raw_text
    return " ".join(words[:nr_of_words-1]) + "..."

@register.filter
def divide(a, b):
    return a//b
