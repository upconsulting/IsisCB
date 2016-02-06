from django.contrib import admin
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.admin import GenericTabularInline, GenericStackedInline
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet, generic_inlineformset_factory
from django import forms
from django.forms import widgets, formsets, models
from django.forms.models import BaseModelFormSet, BaseInlineFormSet, inlineformset_factory
from isisdata.models import *
from simple_history.admin import SimpleHistoryAdmin

import autocomplete_light


# TODO: The Choice widget cannot handle this many choices. Consider using an
#  autocomplete, or some other widget that loads ``object`` choices dynamically
#  via AJAX.
class CCRelationForm(forms.ModelForm):
    class Meta:
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
    class Meta:
        model = ACRelation
        fields = '__all__'

    # class Media:
        # js = ('isisdata/js/autocomplete.js',)
        # css = {
        #     # 'all': ['isisdata/css/autocomplete.css']
        # }


class ACRelationInlineForm(autocomplete_light.ModelForm):
    id = forms.CharField(widget=forms.HiddenInput(), required=False)

    # authority = AutocompleteField(widget=forms.HiddenInput(), model=Authority)
    # authority_name = forms.CharField(widget=AutocompleteWidget(attrs={'class': 'autocomplete'}, datatarget='authority'))

    class Meta:
        model = ACRelation
        fields = (
            # 'authority_name',
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

        # The value of `authority` from the ACRelation is represented with a
        #  hidden field and a separate field, ``authority_name`` is used for
        #  collecting user input and driving the autocomplete. When displaying
        #  an inline for an existing ACRelation, we need to automatically
        #  populate the ``authority`` field on the form.
        # if 'authority' in self.initial:
        #     authority_pk = self.initial['authority']
        #     authority = Authority.objects.get(pk=authority_pk)
        #     self.fields['authority_name'].initial = authority.name


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
                                 for f, v in self.widgets.items()])
        if value is None:
            value = ''
        return "<span class='dynamicWidget' value='{0}'>Select an attribute type</span><script>{1}</script>".format(value, assignments)


class ValueField(forms.Field):
    pass


class AttributeInlineForm(forms.ModelForm):
    class Media:
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
        self.base_fields['type_controlled'].widget.attrs['class'] = css_class

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

    class Media:
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


class CitationForm(autocomplete_light.ModelForm):
    class Meta:
        model = Citation
        fields = '__all__'

    class Media:
        js = ('isisdata/js/jquery-ui.min.js', 'isisdata/js/autocomplete.js',)
        css = {
            'all': ['isisdata/css/autocomplete.css']
        }


class CitationAdmin(SimpleHistoryAdmin,
                    AttributeInlineMixin,
                    LinkedDataInlineMixin,
                    UberInlineMixin):



    list_display = ('id', 'title', 'modified_on', 'modified_by',)
    list_filter = ('type_controlled', 'status_of_record')
    inlines = (ACRelationInline, )
    search_fields = ('title', )
    readonly_fields = ('uri', 'id', 'modified_on_fm','modified_by_fm')

    fieldsets = [
        (None, {
            'fields': (#'uri',
                       #'id',
                       'title',
                       'abstract',
                       'language',
                       'type_controlled'),
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



    form = CitationForm


class AuthorityForm(autocomplete_light.ModelForm):
    class Meta:
        model = Authority
        fields = '__all__'


class AuthorityAdmin(SimpleHistoryAdmin,
                     AttributeInlineMixin,
                     LinkedDataInlineMixin,
                     UberInlineMixin):
    list_display = ('name', 'type_controlled', 'id',)
    list_filter = ('type_controlled', 'record_status')
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


class ACRelationAdmin(SimpleHistoryAdmin,
                      AttributeInlineMixin,
                      LinkedDataInlineMixin,
                      UberInlineMixin):

    list_display = ('id',
                    'authority',
                    'type_controlled',
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


class CCRelationForm(autocomplete_light.ModelForm):
    class Meta:
        model = CCRelation
        fields = '__all__'


class CCRelationAdmin(SimpleHistoryAdmin,
                      AttributeInlineMixin,
                      LinkedDataInlineMixin,
                      UberInlineMixin):

    list_display = ('id',
                    'subject',
                    '_render_type_controlled',
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


class AARelationForm(autocomplete_light.ModelForm):
    class Meta:
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

    list_display = ('id',
                    'subject',
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
    list_display = ('id', 'source', 'type_controlled', 'value')
    inlines = (ValueInline,)


class AttributeTypeAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'name', 'value_content_type')
    list_display_links = ('id', 'name')
    inlines = []

    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}


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
    list_display = ('id', 'snippet', 'created_by', 'subject', 'created_on')
    list_display_links = ('id', 'snippet')
    fields = ('id', 'created_by', 'created_on', 'subject', 'text')
    readonly_fields = ('id', 'created_by', 'created_on', 'subject', 'text')
    inlines = []


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
