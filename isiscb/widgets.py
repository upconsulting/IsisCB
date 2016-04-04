from django.forms.widgets import Widget
from django.forms.utils import flatatt
from django.utils.html import conditional_escape, format_html, html_safe


class AutocompleteWidget(Widget):
    search_model = None
    search_queryset = None
    min_characters = 3
    default_label_field = 'title'
    default_description_field = 'description'

    def __init__(self, *args, **kwargs):
        super(AutocompleteWidget, self).__init__(*args, **kwargs)
        self.label_field = getattr(self, 'label_field', self.default_label_field)
        self.description_field = getattr(self, 'description_field', self.default_description_field)

        # We need braces for angular templating.
        self.openbraces = u'{{'
        self.closebraces = u'}}'

    def value_from_datadict(self, data, files, name):
        instance_id = data.get(name)
        return self.search_model.objects.get(pk=instance_id)

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''

        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_text(self._format_value(value))
            """
            <div ng-controller="autocompleteController">
                <div class="form-group">
                    <input type="text" class="form-control" name="{name}" />
                </div>
                <ul class="list-group autocomplete-search-results" name="{name}_results">
                    <a class="list-group-item" ng-repeat="result in results">{openbraces} result.{label_field} {closebraces}</li>
                </ul>
            </div>
            """
        return format_html('<div{} />', flatatt(div_attrs))
