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


class CCRelationInline(admin.TabularInline):
    fk_name = 'subject'
    model = CCRelation
    form = CCRelationForm
    extra = 1


class ValueWidget(widgets.Widget):
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
        js = ('isisdata/js/widgetmap.js', )

    id = forms.CharField(widget=forms.HiddenInput(), required=False)
    value = ValueField(label='Value', widget=ValueWidget())

    def __init__(self, *args, **kwargs):
        # This CSS class allows us to watch for changes in the selected type, so
        #  that we can dynamically change the widget for ``value``.
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

    def is_valid(self):
        val = super(LinkedDataInlineForm, self).is_valid()
        print self.errors
        return val


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

    extra = 1

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
    extra = 1

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


class CitationForm(autocomplete_light.ModelForm):
    class Meta:
        model = Citation
        fields = '__all__'


class CitationAdmin(SimpleHistoryAdmin,
                    AttributeInlineMixin,
                    LinkedDataInlineMixin,
                    UberInlineMixin):

    list_display = ('id', 'title', 'modified_on_fm', 'modified_by_fm')
    list_filter = ('type_controlled', 'status_of_record')

    fieldsets = [
        (None, {
            'fields': ('uri',
                       'id',
                       'title',
                       'description',
                       'language',
                       'type_controlled')
        }),
        ('Additional Details', {
            'fields': ('abstract',
                       'edition_details',
                       'physical_details')
        }),
        ('Curation', {
            'fields': ('record_action',
                       'status_of_record',
                       'administrator_notes',
                       'record_history',
                       'modified_by_fm',
                       'modified_on_fm')
        }),
    ]

    readonly_fields = ('uri', 'id', 'modified_on_fm','modified_by_fm')

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

    fieldsets = [
        (None, {
            'fields': ('uri',
                       'id',
                       'name',
                       'description',
                       'type_controlled')
        }),
        ('Classification', {
            'fields': ('classification_system',
                       'classification_code',
                       'classification_hierarchy')
        }),
        ('Curation', {
            'fields': ('record_status',
                       'redirect_to',
                       'administrator_notes',
                       'record_history',
                       'modified_by_fm',
                       'modified_on_fm')
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


class ACRelationForm(autocomplete_light.ModelForm):
    class Meta:
        model = ACRelation
        fields = '__all__'


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
admin.site.register(PartDetails, SimpleHistoryAdmin)
admin.site.register(Attribute, AttributeAdmin)
admin.site.register(AttributeType, AttributeTypeAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(SearchQuery)
admin.site.register(Language)
# Register your models here.
