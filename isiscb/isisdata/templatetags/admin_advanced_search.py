from django.contrib.admin.views.main import SEARCH_VAR

from django.template import Library

register = Library()

@register.filter(name='advanced_search_form')
def advanced_search_form(context, cl):
    """
    Displays a search form for searching the list.
    """
    return {
        'advanced_search_form' : context.get('advanced_search_form'),
        'cl': cl,
        'show_result_count': cl.result_count != cl.full_result_count,
        'search_var': SEARCH_VAR
    }
