from django import template
register = template.Library()

@register.filter(name='addcss')
def addcss(field, css):
    if type(field) is str:
        return field
    parts = css.split(';')
    placeholder = parts[1] if len(parts) == 2 else ''
    css = parts[0]

    return field.as_widget(attrs={"class": css, "placeholder": placeholder})
