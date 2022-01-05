from __future__ import unicode_literals
from django.forms import modelform_factory, formset_factory
from django.forms.widgets import *
from isisdata.models import *
from curation.forms import *


def _create_attribute_value_forms():
    value_forms = {}
    for at in AttributeType.objects.all():
        value_class = at.value_content_type.model_class()
        if value_class is ISODateValue:
            value_forms[at.id] = ISODateValueForm
        elif value_class is AuthorityValue:
            value_forms[at.id] = AuthorityValueForm
        elif value_class is CitationValue:
            value_forms[at.id] = CitationValueForm
        else:
            value_forms[at.id] = modelform_factory(value_class,
                                    exclude=('attribute', 'child_class'))
    return value_forms
