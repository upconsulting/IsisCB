
import autocomplete_light.shortcuts as al
from models import *



class AuthorityAutocomplete(al.AutocompleteModelBase):
    """
    TODO: move choice widget styling to external stylesheet.
    """
    choice_html_format = u'''
        <span style="max-width: 600px; overflow-x: scroll;" class="block" data-value="%s">%s - <span class="text-muted">%s</span></span>
    '''

    def choice_html(self, choice):
        return self.choice_html_format % (self.choice_value(choice), self.choice_label(choice), choice.description)

    search_fields=['^name', ]

    autocomplete_js_attributes = {
        'minimum_characters': 3,
    }

    widget_js_attributes = {
        'max_values': 1,
    }


al.register(Authority, AuthorityAutocomplete)


al.register(Language,
    search_fields=['^name', '^id'],
    attrs={
        'placeholder': 'Language ?',
        'data-autocomplete-minimum-characters': 3,
    },
    widget_attrs={
        'data-widget-maximum-values': 10,
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
