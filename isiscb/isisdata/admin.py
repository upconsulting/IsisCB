from __future__ import unicode_literals
from builtins import zip
from builtins import object
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.admin import GenericTabularInline, GenericStackedInline
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet, generic_inlineformset_factory
from django import forms
from django.forms import widgets, formsets, models
from django.forms.models import BaseModelFormSet, BaseInlineFormSet, inlineformset_factory
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from isisdata.models import *
from simple_history.admin import SimpleHistoryAdmin

from dal import autocomplete


def as_datetime(x):
    formats = ['%m/%d/%Y %I:%M:%S %p', '%m/%d/%Y %I:%M %p', '%m/%d/%Y', '%Y']
    val = None
    for format in formats:
        try:
            val = datetime.datetime.strptime(x, format)
        except ValueError:
            pass
    # if val is None:
    #     raise ValueError('Could not coerce value to datetime')
    return val


# TODO: The Choice widget cannot handle this many choices. Consider using an
#  autocomplete, or some other widget that loads ``object`` choices dynamically
#  via AJAX.
class CCRelationForm(forms.ModelForm):
    class Meta(object):
        model = CCRelation
        fields = ('object', )


class AutocompleteWidget(widgets.TextInput):
    def __init__(self, *args, **kwargs):
        self.datatarget = kwargs.get('datatarget', None)
        if self.datatarget:
            del kwargs['datatarget']
        return super(AutocompleteWidget, self).__init__(*args, **kwargs)

    def _format_value(self, value):
        if self.is_localized:
            return formats.localize_input(value)
        return value

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
        # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = widgets.force_text(self._format_value(value))

        if 'class' not in final_attrs:
            final_attrs['class'] = ''
        final_attrs['class'] += ' autocomplete form-control'

        if self.datatarget:
            final_attrs['datatarget'] = self.datatarget

        return widgets.format_html('<div class="input-group" id="'+ final_attrs['id'] +'_container"><input{} /><span class="autocomplete-status input-group-addon"></span></div>', widgets.flatatt(final_attrs))


class AutocompleteField(forms.CharField):
    def __init__(self, *args, **kwargs):
        self.model = kwargs.get('model', None)
        if self.model:
            del kwargs['model']

        super(AutocompleteField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if not self.model:
            return None
        if value in self.empty_values:
            return None
        try:
            value = self.model.objects.get(**{'pk': value})
        except (ValueError, TypeError):
            raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice')
        return value


class ACRelationForm(forms.ModelForm):
    class Meta(object):
        model = ACRelation
        fields = '__all__'

    # class Media:
        # js = ('isisdata/js/autocomplete.js',)
        # css = {
        #     # 'all': ['isisdata/css/autocomplete.css']
        # }


class ACRelationInlineForm(forms.ModelForm):
    id = forms.CharField(widget=forms.HiddenInput(), required=False)

    authority = AutocompleteField(widget=forms.HiddenInput(), model=Authority)
    authority_name = forms.CharField(widget=AutocompleteWidget(attrs={'class': 'autocomplete'}, datatarget='authority'))

    class Meta(object):
        model = ACRelation
        fields = (
            'authority_name',
            'authority',
            'name_for_display_in_citation',
            'name_as_entered',
            'type_controlled',
            'type_broad_controlled',
            'type_free',
            'data_display_order',
            )

    def __init__(self, *args, **kwargs):
        super(ACRelationInlineForm, self).__init__(*args, **kwargs)

        for key, field in list(self.fields.items()):
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = ''
            field.widget.attrs['class'] += ' form-control'
        # The value of `authority` from the ACRelation is represented with a
        #  hidden field and a separate field, ``authority_name`` is used for
        #  collecting user input and driving the autocomplete. When displaying
        #  an inline for an existing ACRelation, we need to automatically
        #  populate the ``authority`` field on the form.
        if 'authority' in self.initial:
            authority_pk = self.initial['authority']
            authority = Authority.objects.get(pk=authority_pk)
            self.fields['authority_name'].initial = authority.name


class CCRelationInline(admin.TabularInline):
    fk_name = 'subject'
    model = CCRelation
    form = CCRelationForm
    extra = 1


class ACRelationInline(admin.StackedInline):
    fk_name = 'citation'
    model = ACRelation
    form = ACRelationInlineForm
    extra = 0



class ValueWidget(widgets.Widget):
    """
    Supports dynamically setting input widget based on the values of other
    fields.
    """
    def __init__(self, attrs=None):
        super(ValueWidget, self).__init__(attrs)

        self.widgets = {
            'textvalue': widgets.TextInput(),
            'datetimevalue': widgets.DateTimeInput(),
            'intvalue': widgets.NumberInput(),
            'floatvalue': widgets.NumberInput(),
            'charvalue': widgets.TextInput(),
            'datevalue': widgets.DateInput(),
            'locationvalue': widgets.TextInput(), # TODO: custom location widget
        }

    def render(self, name, value, attrs=None):
        assign = "widgets.{0} = $('{1}')[0];";
        assignments = '\n'.join([assign.format(f,v.render(name, value, attrs))
                                 for f, v in list(self.widgets.items())])
        if value is None:
            value = ''
        return "<span class='dynamicWidget' value='{0}'>Select an attribute type</span><script>{1}</script>".format(value, assignments)


class ValueField(forms.Field):
    pass


class AttributeInlineForm(forms.ModelForm):
    class Meta(object):
        model = Attribute
        exclude = []

    class Media(object):
        model = Attribute

        # widgetmap.js sets the widget for ``value`` based on the user's
        #  selection in the ``type_controlled`` field.
        js = ('isisdata/js/widgetmap.js', )

    id = forms.CharField(widget=forms.HiddenInput(), required=False)
    value = ValueField(label='Value', widget=ValueWidget())

    def __init__(self, *args, **kwargs):
        # This CSS class allows us to watch for changes in the selected type, so
        #  that we can dynamically change the widget for ``value``. See
        #  widgetmap.js, referenced above.
        css_class = 'attribute_type_controlled'
        try:
            self.base_fields['type_controlled'].widget.attrs['class'] = css_class
        except KeyError:
            pass

        super(AttributeInlineForm, self).__init__(*args, **kwargs)

        # Populate value and id fields.
        instance = kwargs.get('instance', None)
        if instance is not None:
            value_initial = instance.value.cvalue()
            self.fields['value'].initial = value_initial
            self.fields['id'].initial = instance.id

    def is_valid(self):
        """
        Enforce validation for ``value`` based on ``type_controlled``.
        """
        val = super(AttributeInlineForm, self).is_valid()

        if all(x in self.cleaned_data for x in ['value', 'type_controlled']):
            value = self.cleaned_data['value']
            attr_type = self.cleaned_data['type_controlled']
            value_model = attr_type.value_content_type.model_class()
            try:
                value_model.is_valid(value)
            except ValidationError as E:
                self.add_error('value', E)
        return super(AttributeInlineForm, self).is_valid()


class AttributeInlineFormSet(BaseGenericInlineFormSet):
    model = Attribute


class LinkedDataInlineForm(forms.ModelForm):
    model = LinkedData

    class Media(object):
        model = LinkedData
        js = ('isisdata/js/widgetmap.js', )

    id = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):

        super(LinkedDataInlineForm, self).__init__(*args, **kwargs)
        # Populate value and id fields.
        instance = kwargs.get('instance', None)
        if instance is not None:
            self.fields['id'].initial = instance.id

    def clean(self):
        cleaned_data = super(LinkedDataInlineForm, self).clean()

        # Enforce LinkedDataType pattern validation.
        value = self.cleaned_data['universal_resource_name']
        # Raises a ValidationError if value does not match pattern for this
        #  LinkedDataType.
        self.cleaned_data['type_controlled'].is_valid(value)

        return self.cleaned_data


class LinkedDataInlineFormSet(BaseGenericInlineFormSet):
    model = LinkedData


class LinkedDataInline(GenericTabularInline):
    model = LinkedData
    form = LinkedDataInlineForm

    formset = generic_inlineformset_factory(LinkedData,
                                            form=LinkedDataInlineForm,
                                            formset=LinkedDataInlineFormSet,
                                            ct_field='subject_content_type',
                                            fk_field='subject_instance_id')

    ct_field = 'subject_content_type'
    ct_fk_field = 'subject_instance_id'

    extra = 0

    fields = ('type_controlled',
              'type_controlled_broad',
              'type_free',
              'universal_resource_name',
              'id')

    exclude = ('administrator_notes',
               'record_history',
               'modified_on_fm',
               'modified_by_fm',
               'modified_by',
               'modified_on',
               'created_on_fm',
               'created_by_fm',
               'place',
               'date_iso',
               'id',
               'uri',
               'description')


class LinkedDataInlineMixin(admin.ModelAdmin):
    def __init__(self, *args, **kwargs):
        if hasattr(self, 'inlines'):
            if LinkedDataInline not in self.inlines:
                self.inlines += (LinkedDataInline,)
        else:
            self.inlines = (LinkedDataInline,)
        super(LinkedDataInlineMixin, self).__init__(*args, **kwargs)


class AttributeInline(GenericTabularInline):
    model = Attribute
    form = AttributeInlineForm
    # formset = AttributeInlineFormSet
    formset = generic_inlineformset_factory(Attribute,
                                            form=AttributeInlineForm,
                                            formset=AttributeInlineFormSet,
                                            ct_field='source_content_type',
                                            fk_field='source_instance_id')
    extra = 0

    ct_field = 'source_content_type'
    ct_fk_field = 'source_instance_id'

    fields = ('type_controlled',
              'type_controlled_broad',
              'type_free',
              'value',
              'value_freeform',
              'id')

    exclude = ('administrator_notes',
               'record_history',
               'modified_on_fm',
               'modified_by_fm',
               'modified_by',
               'modified_on',
               'created_on_fm',
               'created_by_fm',
               'place',
               'date_iso',
               'id',
               'uri',
               'description')


class AttributeInlineMixin(admin.ModelAdmin):
    def __init__(self, *args, **kwargs):
        if hasattr(self, 'inlines'):
            if AttributeInline not in self.inlines:
                self.inlines += (AttributeInline,)
        else:
            self.inlines = (AttributeInline,)
        super(AttributeInlineMixin, self).__init__(*args, **kwargs)


class UberInlineMixin(admin.ModelAdmin):
    def save_formset(self, request, form, formset, change):
        """
        Given an inline formset save it to the database.
        """
        return formset.save(commit=False)

    def save_related(self, request, form, formsets, change):
        """
        Generate a new ``Value`` instance for each ``Attribute``.
        """
        form.save_m2m()     # Does not include Attributes.

        for formset in formsets:
            # Look only at the Attribute formset.
            if type(formset).__name__ == 'AttributeFormFormSet':
                instances = self.save_formset(request, form, formset,
                                              change=change)
                for attribute, data in zip(instances, formset.cleaned_data):
                    attr_type, value = data['type_controlled'], data['value']
                    value_model = attr_type.value_content_type.model_class()
                    attribute.save()
                    if hasattr(attribute, 'value'):   # Modifying existing attr.
                        value_instance = attribute.value.get_child_class()
                        if value_instance.value != value:
                            value_instance.value = value
                            value_instance.save()
                    else:                             # Creating a new attr.
                        value_instance = value_model(attribute=attribute,
                                                     value=value)
                        value_instance.save()
                    attribute.save()


            elif type(formset).__name__ == 'LinkedDataFormFormSet':
                instances = self.save_formset(request, form, formset,
                                              change=change)
                formset.save_m2m()
                formset.save()
            else:
                instances = self.save_formset(request, form, formset,
                                              change=change)
                formset.save_m2m()
                formset.save()


class AdvancedSearchMixin(object):
    """
    Provides advanced search functionality for ModelAdmin.
    """
    def apply_advanced_search(self, request, queryset):
        if not hasattr(self, 'other_search_fields'):    # No advanced search.
            return queryset

        # Apply filtering from advanced search form.
        for key, value in list(self.other_search_fields.items()):
            if key in getattr(self, 'advanced_search_icontains_fields', {}):
                param = {'%s__icontains' % key : value}
            elif key in getattr(self, 'advanced_search_exact_fields', {}):
                param = {key : value}
            elif key in getattr(self, 'advanced_search_date_fields', {}):
                field = self.advanced_search_date_fields[key]
                value = as_datetime(value).strftime('%Y-%m-%d')
                param = {field : value}
            elif key in getattr(self, 'advanced_search_related_fields', {}):
                field, related_key, related_field = self.advanced_search_related_fields[key]
                if related_key not in self.other_search_fields:
                    continue
                related_value = self.other_search_fields[related_key]
                param = {field : value, related_field: related_value}
            elif key in getattr(self, 'advanced_search_related_direct', {}):
                field = self.advanced_search_related_direct[key]
                param = {field: value}
            else:
                continue
            queryset = queryset.filter(**param).distinct('pk')
        return queryset

    def advanced_search_extra_context(self, request, **kwargs):
        extra_context = kwargs.get('extra_context', {})
        self.other_search_fields = {}
        # TODO: initial data?

        request.GET._mutable=True
        for key in list(self.advanced_search_form().fields.keys()):
            try:
                temp = request.GET.pop(key)
            except KeyError:
                pass # there is no field of the form in the dict so we don't remove it
            else:
                if temp!=['']: #there is a field but it's empty so it's useless
                    self.other_search_fields[key] = temp[0]

        extra_context = {
            'advanced_search_form': self.advanced_search_form(initial=self.other_search_fields),
            'advanced_search_form_template': self.advanced_search_form_template,
            'searching': len(self.other_search_fields) > 0,
        }
        request.GET_mutable=False

        return extra_context


class CitationAdvancedSearchForm(forms.Form):
    """
    Provides advanced search fields in the Citation changelist view.
    """
    # Search by __icontains:
    title = forms.CharField(required=False)
    abstract = forms.CharField(required=False)
    description = forms.CharField(required=False)
    edition_details = forms.CharField(required=False)
    physical_details = forms.CharField(required=False)

    # Discrete choices:
    status_of_record = forms.ChoiceField(choices=[('', 'All')] + list(Citation.STATUS_CHOICES), required=False)
    record_action = forms.ChoiceField(choices=[('', 'All')] + list(Citation.ACTION_CHOICES), required=False)
    language = forms.ModelChoiceField(queryset=Language.objects.all(), required=False)
    type_controlled = forms.ChoiceField(choices=[('', 'All')] + list(Citation.TYPE_CHOICES), required=False)

    # Limit by range. TODO: add field validation for date format.
    published_after = forms.DateField(required=False, widget=forms.DateInput(attrs={'placeholder': 'YYYY-MM-DD'}))
    published_before = forms.DateField(required=False, widget=forms.DateInput(attrs={'placeholder': 'YYYY-MM-DD'}))

    # Authority
    relation_type = forms.ChoiceField(choices=[('', 'All')] + list(ACRelation.TYPE_CHOICES), required=False)
    authority_name = forms.CharField(required=False)


class CitationForm(forms.ModelForm):
    class Meta(object):
        model = Citation
        fields = '__all__'

    class Media(object):
        js = ('isisdata/js/jquery-ui.min.js', 'isisdata/js/autocomplete.js',)
        css = {
            'all': ['isisdata/css/autocomplete.css']
        }

    def __init__(self, *args, **kwargs):
        super(CitationForm, self).__init__(*args, **kwargs)
        for key, field in list(self.fields.items()):
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = ''
            field.widget.attrs['class'] += ' form-control'


class CitationAdmin(SimpleHistoryAdmin,
                    AttributeInlineMixin,
                    LinkedDataInlineMixin,
                    UberInlineMixin,
                    AdvancedSearchMixin):


    form = CitationForm
    list_display = ('id', 'title', 'type_controlled', 'modified_on',
                    'modified_by', 'public', 'status_of_record',)

    # Filters in the changelist interfere with the advanced search. We can add
    #  it back, but we will need to find a way to pass the advanced search GET
    #  parameters to the new request when a user clicks on one of the filters.
    #  Since this functionality is replicated in the advanced search form, we'll
    #  just disable ``list_filter`` for now.
    # list_filter = ('type_controlled', 'status_of_record')

    # We need this for now, since it triggers advanced search rendering in the
    #  changelist view. That's hoakie, so TODO: we should fix this.
    search_fields = ('title', )

    # These class attributes control the advanced search behavior.
    advanced_search_form = CitationAdvancedSearchForm
    advanced_search_form_template = 'advanced_search_form_citation'
    advanced_search_icontains_fields = ['title', 'abstract', 'description',
                                        'edition_details', 'physical_details']
    advanced_search_exact_fields = ['type_controlled', 'status_of_record',
                                    'record_action']
    advanced_search_date_fields = dict([
        ('published_before', 'publication_date__lt'),
        ('published_after', 'publication_date__gt')])
    advanced_search_related_fields = dict([
        ('relation_type', (
            'acrelation__type_controlled',      # This search field query.
            'authority_name',                   # Linked search field.
            'acrelation__authority__name__icontains')),     # Linked query.
    ])

    # These class attributes control the change view.
    readonly_fields = ('uri', 'id', 'modified_on_fm', 'modified_by_fm')
    inlines = (ACRelationInline, )

    fieldsets = [
        (None, {
            'fields': (#'uri',
                       #'id',
                       'title',
                       'abstract',
                       'language',
                       'type_controlled',
                       'public'),
            'classes': ('extrapretty',),

        }),
        ('Additional Details', {
            'fields': ('description',
                       'edition_details',
                       'physical_details'),
            'classes': ('extrapretty', 'collapse'),
        }),
        ('Curation', {
            'fields': ('record_action',
                       'status_of_record',
                       'administrator_notes',
                       'record_history'),
           'classes': ('extrapretty', 'collapse'),
        }),
    ]

    def get_queryset(self, request):
        queryset = super(CitationAdmin, self).get_queryset(request)

        return self.apply_advanced_search(request, queryset)

    def changelist_view(self, request, **kwargs):
        extra_context = self.advanced_search_extra_context(request, **kwargs)

        return super(CitationAdmin, self).changelist_view(request, extra_context=extra_context)

    def lookup_allowed(self, lookup, *args, **kwargs):
        if lookup in list(self.advanced_search_form().fields.keys()):
            return True
        return super(CitationAdmin, self).lookup_allowed(lookup, *args, **kwargs)


class AuthorityAdvancedSearchForm(forms.Form):
    """
    Provides advanced search fields in the Citation changelist view.
    """
    # Search by __icontains:
    name = forms.CharField(required=False)
    description = forms.CharField(required=False)

    # Discrete choices:
    record_status = forms.ChoiceField(choices=[('', 'All')] + list(Authority.STATUS_CHOICES), required=False)
    classification_system = forms.ChoiceField(choices=[('', 'All')] + list(Authority.CLASS_SYSTEM_CHOICES), required=False)
    type_controlled = forms.ChoiceField(choices=[('', 'All')] + list(Authority.TYPE_CHOICES), required=False)

    # Authority
    relation_type = forms.ChoiceField(choices=[('', 'All')] + list(ACRelation.TYPE_CHOICES), required=False)
    citation_title = forms.CharField(required=False)

    # ISISCB-392: This may require changing Value from concrete to abstract, to
    #  allow us to directly join its children's tables. Commented pending a
    #  decision.
    # attribute_type = forms.ModelChoiceField(queryset=AttributeType.objects.all(), required=False)
    # attribute_value = forms.CharField(required=False)


class AuthorityForm(forms.ModelForm):
    class Meta(object):
        model = Authority
        fields = '__all__'


class AuthorityAdmin(SimpleHistoryAdmin,
                     AttributeInlineMixin,
                     LinkedDataInlineMixin,
                     UberInlineMixin,
                     AdvancedSearchMixin):
    list_display = ('name', 'type_controlled', 'id',)
    # list_filter = ('type_controlled', 'record_status')
    search_fields = ('name', )

    fieldsets = [
        (None, {
            'fields': (#'uri',
                       #'id',
                       'name',
                       'description',
                       'type_controlled',
                       'public'),
            'classes': ('extrapretty',),
        }),
        ('Classification', {
            'fields': ('classification_system',
                       'classification_code',
                       'classification_hierarchy'),
            'classes': ('extrapretty', 'collapse'),
        }),
        ('Curation', {
            'fields': ('record_status',
                       'redirect_to',
                       'administrator_notes',
                       'record_history',
                       'modified_by_fm',
                       'modified_on_fm'),
            'classes': ('extrapretty', 'collapse'),
        }),
    ]
    readonly_fields = ('uri',
                       'id',
                       'classification_system',
                       'classification_code',
                       'classification_hierarchy',
                       'modified_on_fm',
                       'modified_by_fm')

    form = AuthorityForm

    advanced_search_form = AuthorityAdvancedSearchForm
    advanced_search_form_template = 'advanced_search_form_authority'
    advanced_search_icontains_fields = ['name', 'description']
    advanced_search_exact_fields = ['type_controlled', 'record_status',
                                    'classification_system']

    advanced_search_related_fields = dict([
        ('relation_type', (
            'acrelation__type_controlled',      # This search field query.
            'citation_title',                   # Linked search field on Form.
            'acrelation__citation__title__icontains'    # Linked query.
            )
        ),
        # ISISCB-392: This may require changing Value from concrete to abstract,
        #  to allow us to directly join its children's tables. Commented pending
        #  a decision.
        # ('attribute_type', (
        #     'attributes__type_controlled',
        #     'attribute_value',
        #     'attributes__value__{child_class}__value'
        #     )
        # )
    ])




    def get_queryset(self, request):
        queryset = super(AuthorityAdmin, self).get_queryset(request)

        return self.apply_advanced_search(request, queryset)

    def changelist_view(self, request, **kwargs):
        extra_context = self.advanced_search_extra_context(request, **kwargs)

        return super(AuthorityAdmin, self).changelist_view(request, extra_context=extra_context)

    def lookup_allowed(self, lookup, *args, **kwargs):
        if lookup in list(self.advanced_search_form().fields.keys()):
            return True
        return super(AuthorityAdmin, self).lookup_allowed(lookup, *args, **kwargs)


class ACRelationAdvancedSearchForm(forms.Form):
    """
    Provides advanced search fields in the Citation changelist view.
    """
    # Search by __icontains:
    name = forms.CharField(required=False)
    description = forms.CharField(required=False)
    type_free = forms.CharField(required=False)

    # Discrete choices:
    type_controlled = forms.ChoiceField(choices=[('', 'All')] + list(ACRelation.TYPE_CHOICES), required=False)
    type_broad_controlled = forms.ChoiceField(choices=[('', 'All')] + list(ACRelation.BROAD_TYPE_CHOICES), required=False)

    # Related fields.
    citation_type = forms.ChoiceField(choices=[('', 'All')] + list(Citation.TYPE_CHOICES), required=False)
    citation_title = forms.CharField(required=False)
    authority_type = forms.ChoiceField(choices=[('', 'All')] + list(Authority.TYPE_CHOICES), required=False)
    authority_name = forms.CharField(required=False)


class ACRelationAdmin(SimpleHistoryAdmin,
                      AttributeInlineMixin,
                      LinkedDataInlineMixin,
                      UberInlineMixin,
                      AdvancedSearchMixin):

    list_display = ('id', 'name',
                    'authority',
                    'type_controlled',
                    'type_broad_controlled',
                    'type_free',
                    'citation')

    fieldsets = [
        (None, {
            'fields': ('uri',
                       'id',
                       'citation',
                       'authority',
                       'name',
                       'name_for_display_in_citation',
                       'description')
        }),
        ('Type', {
            'fields': ('type_controlled',
                       'type_broad_controlled',
                       'type_free')
        }),
        ('Curation', {
            'fields': ('administrator_notes',
                       'record_history',
                       'modified_by_fm',
                       'modified_on_fm')
        }),
    ]

    readonly_fields = ('uri',
                       'id',
                       'modified_by_fm',
                       'modified_on_fm')

    form = ACRelationForm
    search_fields = ('name', )

    advanced_search_form = ACRelationAdvancedSearchForm
    advanced_search_form_template = 'advanced_search_form_acrelation'
    advanced_search_icontains_fields = ['name', 'description', 'type_free']
    advanced_search_exact_fields = ['type_controlled',
                                    'type_broad_controlled',]

    advanced_search_related_direct = {
        'citation_type': 'citation__type_controlled',
        'citation_title': 'citation__title__icontains',
        'authority_type': 'authority__type_controlled',
        'authority_name': 'authority__name__icontains',
    }

    def get_queryset(self, request):
        queryset = super(ACRelationAdmin, self).get_queryset(request)

        return self.apply_advanced_search(request, queryset)

    def changelist_view(self, request, **kwargs):
        extra_context = self.advanced_search_extra_context(request, **kwargs)

        return super(ACRelationAdmin, self).changelist_view(request, extra_context=extra_context)

    def lookup_allowed(self, lookup, *args, **kwargs):
        if lookup in list(self.advanced_search_form().fields.keys()):
            return True
        return super(ACRelationAdmin, self).lookup_allowed(lookup, *args, **kwargs)


class CCRelationAdvancedSearchForm(forms.Form):
    """
    Provides advanced search fields in the Citation changelist view.
    """
    # Search by __icontains:
    name = forms.CharField(required=False)
    description = forms.CharField(required=False)
    type_free = forms.CharField(required=False)

    # Discrete choices:
    type_controlled = forms.ChoiceField(choices=[('', 'All')] + list(CCRelation.TYPE_CHOICES), required=False)

    # Related fields.
    source_type = forms.ChoiceField(choices=[('', 'All')] + list(Citation.TYPE_CHOICES), required=False)
    source_title = forms.CharField(required=False)
    object_type = forms.ChoiceField(choices=[('', 'All')] + list(Citation.TYPE_CHOICES), required=False)
    object_title = forms.CharField(required=False)


class CCRelationForm(forms.ModelForm):
    class Meta(object):
        model = CCRelation
        fields = '__all__'


class CCRelationAdmin(SimpleHistoryAdmin,
                      AttributeInlineMixin,
                      LinkedDataInlineMixin,
                      UberInlineMixin,
                      AdvancedSearchMixin):

    list_display = ('id',
                    'subject',
                    'type_controlled',
                    'object')

    fieldsets = [
        (None, {
            'fields': ('uri',
                       'id',
                       'subject',
                       'object',
                       'name',
                       'description')
        }),
        ('Type', {
            'fields': ('type_controlled',
                       'type_free')
        }),
        ('Curation', {
            'fields': ('administrator_notes',
                       'record_history',
                       'modified_by_fm',
                       'modified_on_fm')
        }),
    ]

    readonly_fields = ('uri',
                       'id',
                       'modified_by_fm',
                       'modified_on_fm')

    form = CCRelationForm
    search_fields = ('name',)

    advanced_search_form = CCRelationAdvancedSearchForm
    advanced_search_form_template = 'advanced_search_form_ccrelation'
    advanced_search_icontains_fields = ['name', 'description', 'type_free']
    advanced_search_exact_fields = ['type_controlled',]

    advanced_search_related_direct = {
        'subject_type': 'subject__type_controlled',
        'subject_title': 'subject__title__icontains',
        'object_type': 'object__type_controlled',
        'object_title': 'object__title__icontains',
    }

    def get_queryset(self, request):
        queryset = super(CCRelationAdmin, self).get_queryset(request)

        return self.apply_advanced_search(request, queryset)

    def changelist_view(self, request, **kwargs):
        extra_context = self.advanced_search_extra_context(request, **kwargs)

        return super(CCRelationAdmin, self).changelist_view(request, extra_context=extra_context)

    def lookup_allowed(self, lookup, *args, **kwargs):
        if lookup in list(self.advanced_search_form().fields.keys()):
            return True
        return super(CCRelationAdmin, self).lookup_allowed(lookup, *args, **kwargs)


class AARelationForm(forms.ModelForm):
    class Meta(object):
        model = AARelation
        fields = '__all__'


class AARelationAdmin(SimpleHistoryAdmin,
                      AttributeInlineMixin,
                      LinkedDataInlineMixin,
                      UberInlineMixin):

    list_display = ('id',
                    'subject',
                    'type_controlled',
                    'object')

    search_fields = ('name',)

    fieldsets = [
        (None, {
            'fields': ('uri',
                       'id',
                       'subject',
                       'object',
                       'name',
                       'description')
        }),
        ('Type', {
            'fields': ('type_controlled',
                       'type_free')
        }),
        ('Curation', {
            'fields': ('administrator_notes',
                       'record_history',
                       'modified_by_fm',
                       'modified_on_fm')
        }),
    ]

    readonly_fields = ('uri',
                       'id',
                       'modified_by_fm',
                       'modified_on_fm')

    form = AARelationForm


class LinkedDataTypeAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'pattern')
    inlines = []



class LinkedDataAdmin(SimpleHistoryAdmin):
    search_fields = ('universal_resource_name',)
    list_display = ('id',
                    # 'subject',
                    'type_controlled',
                    'universal_resource_name')
    list_filter = ('type_controlled',)


    fieldsets = [
        (None, {
            'fields': ('uri',
                       'id',
                       'universal_resource_name',
                       'description',
                       'subject_content_type',
                       'subject_instance_id')
        }),
        ('Type', {
            'fields': ('type_controlled',
                       'type_controlled_broad',
                       'type_free')
        }),
        ('Curation', {
            'fields': ('administrator_notes',
                       'record_history',
                       'modified_by_fm',
                       'modified_on_fm')
        }),
    ]

    readonly_fields = ('uri',
                       'id',
                       'subject_instance_id',
                       'subject_content_type',
                       'modified_by_fm',
                       'modified_on_fm')

    inlines = []


class ValueInline(admin.StackedInline):
    can_delete = False
    model = Value
    fields = ('cvalue',)
    readonly_fields = ('cvalue', )


class AttributeAdmin(SimpleHistoryAdmin):
    search_fields = ('type_controlled__name',)
    fieldsets = [
        (None, {
            'fields': ('uri',
                       'id',
                       'description',
                       'source_content_type',
                       'source_instance_id')
        }),
        ('Type', {
            'fields': ('type_controlled',
                       'type_controlled_broad',
                       'type_free')
        }),
        ('Curation', {
            'fields': ('administrator_notes',
                       'record_history',
                       'modified_by_fm',
                       'modified_on_fm')
        }),
    ]
    readonly_fields = ('uri', 'id', 'source_content_type', 'source_instance_id')
    list_display = ('id',  'type_controlled', 'value')
    inlines = (ValueInline,)


class AttributeTypeAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'name', 'value_content_type')
    list_display_links = ('id', 'name')
    inlines = []

    # def get_model_perms(self, request):
    #     """
    #     Return empty perms dict thus hiding the model from admin index.
    #     """
    #     return {}


class PartDetailsAdmin(SimpleHistoryAdmin):
    exclude = []

    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}


class SearchQueryAdmin(SimpleHistoryAdmin):
    exclude = []

    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}


class LanguageAdmin(SimpleHistoryAdmin):
    exclude = []

    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}


class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'snippet', 'created_by', 'subject', 'view_record', 'created_on')
    list_display_links = ('id', 'snippet')
    fields = ('id', 'created_by', 'created_on', 'subject', 'text')
    readonly_fields = ('id', 'created_by', 'created_on', 'subject', 'text')
    inlines = []

    def view_record(self, obj, *args, **kwargs):
        return format_html('<a href="{}" target="_blank">View record</a>',
                           mark_safe(obj.subject.get_absolute_url()))


class UserProfileAdmin(admin.ModelAdmin):
    class Meta(object):
        model = UserProfile

    readonly_fields = ['authority_record',]
    search_fields = ('user__username', )
    list_display = ('user', 'affiliation', 'location', 'resolver_institution',
                    'share_email')


class IsisCBUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'last_name', 'first_name', 'date_joined')

    # def joined(self, obj, *args, **kwargs):
    #     return obj.date_joined

class TrackingAdmin(admin.ModelAdmin):
    list_display = ('get_citation_id','type_controlled', 'tracking_info', 'citation')
    list_select_related = (
        'citation',
    )
    readonly_fields = ['citation']
    class Meta(object):
        model = Tracking

    def get_citation_id(self, obj):
        return obj.citation.id
    get_citation_id.short_description = 'Citation ID'
    get_citation_id.admin_order_field = 'citation__id'

class AuthorityTrackingAdmin(admin.ModelAdmin):
    list_display = ('get_authority_id','type_controlled', 'tracking_info', 'authority')
    list_select_related = (
        'authority',
    )
    readonly_fields = ['authority']
    class Meta(object):
        model = AuthorityTracking

    def get_authority_id(self, obj):
        return obj.authority.id
    get_authority_id.short_description = 'Authority ID'
    get_authority_id.admin_order_field = 'authority__id'

class CitationCollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'createdBy', 'citation_count')
    readonly_fields = ['citations']

    def citation_count(self, obj):
        return obj.citations.count()

class CitationSubtypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'unique_name', 'related_citation_type')
    fields = ['name', 'unique_name', 'description', 'related_citation_type']
    exlude = ('attributes')

class DatasetAdmin(admin.ModelAdmin):
    fields = ['name', 'description', 'editor']

class IsisCBRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    readonly_fields = ['users', 'def_dataset_rules', 'def_zotero_rules', 'def_crud_rules']

    def def_dataset_rules(self, obj):
        return DatasetRule.objects.filter(role=obj.pk)

    def def_zotero_rules(self, obj):
        return ZoteroRule.objects.filter(role=obj.pk)

    def def_crud_rules(self, obj):
        return CRUDRule.objects.filter(role=obj.pk)


admin.site.register(Citation, CitationAdmin)
admin.site.register(Authority, AuthorityAdmin)
admin.site.register(ACRelation, ACRelationAdmin)
admin.site.register(CCRelation, CCRelationAdmin)
admin.site.register(AARelation, AARelationAdmin)
admin.site.register(LinkedData, LinkedDataAdmin)
admin.site.register(LinkedDataType, LinkedDataTypeAdmin)
admin.site.register(PartDetails, PartDetailsAdmin)
admin.site.register(Attribute, AttributeAdmin)
admin.site.register(AttributeType, AttributeTypeAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(SearchQuery, SearchQueryAdmin)
admin.site.register(Language, LanguageAdmin)
# Register your models here.
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Tracking, TrackingAdmin)
admin.site.register(AuthorityTracking, AuthorityTrackingAdmin)
admin.site.register(CitationCollection, CitationCollectionAdmin)
#admin.site.register(IsisCBRole, IsisCBRoleAdmin)

admin.site.unregister(User)
admin.site.register(User, IsisCBUserAdmin)

admin.site.register(CitationSubtype, CitationSubtypeAdmin)
admin.site.register(Dataset, DatasetAdmin)
