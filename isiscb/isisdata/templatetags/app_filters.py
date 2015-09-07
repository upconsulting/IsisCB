from django import template

register = template.Library()

@register.filter(name='to_class_name')
def to_class_name(value):
    return value.__class__.__name__

@register.filter(name='joinby')
def joinby(value, arg):
    if arg == None or not arg:
        return ''
    try:
        return arg.join(value)
    except:
        return arg

@register.filter
def get_authors(value):
    if value:
        return value.acrelation_set.filter(type_controlled__in=['AU', 'CO'])
    return value
