from django import template
register = template.Library()

@register.filter(name='addcss')
def addcss(field, css):
    if type(field) is str:
        return field
    parts = css.split(';')
    placeholder = parts[1] if len(parts) == 2 else ''
    css = parts[0]
    other_prop = parts[2] if len(parts) == 3 else ''
    other_prop_list = other_prop.split(":") if other_prop else None
    if other_prop_list:
        return field.as_widget(attrs={"class": css, "placeholder": placeholder, other_prop_list[0]: other_prop_list[1]})
    return field.as_widget(attrs={"class": css, "placeholder": placeholder})
