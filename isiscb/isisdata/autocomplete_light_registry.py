import autocomplete_light.shortcuts as al
from models import *

al.register(Authority,
    search_fields=['^name', ],
    attrs={
        'placeholder': 'Authority entry name ?',
        'data-autocomplete-minimum-characters': 3,
    },
    widget_attrs={
        'data-widget-maximum-values': 1,
        'class': 'modern-style',
    },
)

al.register(Language,
    search_fields=['^name', '^id'],
    attrs={
        'placeholder': 'Language ?',
        'data-autocomplete-minimum-characters': 3,
    },
    widget_attrs={
        'data-widget-maximum-values': 10,
        'class': 'modern-style',
    },
)

al.register(Citation,
    search_fields=['^title', ],
    attrs={
        'placeholder': 'Citation title ?',
        'data-autocomplete-minimum-characters': 3,
    },
    widget_attrs={
        'data-widget-maximum-values': 1,
        'class': 'modern-style',
    },
)
