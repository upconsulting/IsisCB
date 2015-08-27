from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline, GenericStackedInline
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet, generic_inlineformset_factory
from django import forms
from django.forms import widgets, formsets, models
from django.forms.models import BaseModelFormSet, BaseInlineFormSet, inlineformset_factory
from isisdata.models import *
from simple_history.admin import SimpleHistoryAdmin

# TODO: The Choice widget cannot handle this many choices. Consider using an
#  autocomplete, or some other widget that loads ``object`` choices dynamically
#  via AJAX.
class CCRelationForm(forms.ModelForm):
    class Meta:
        model = CCRelation
        fields = ('object', )

    # object = forms.ChoiceField(required=True, choices=CCRelation.objects.values_list('id', 'name'))


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
        return "<span class='dynamicWidget'>Select an attribute type</span><script>{0}</script>".format(assignments)




class ValueField(forms.Field):
    def __init__(self, *args, **kwargs):
        super(ValueField, self).__init__(*args, **kwargs)


class AttributeInlineForm(forms.ModelForm):
    class Media:
        model = Attribute
        js = ('isisdata/js/jquery-1.11.1.min.js',
              'isisdata/js/widgetmap.js')

    value = ValueField(label='Value', widget=ValueWidget()) # TODO: add widget here.

    def __init__(self, *args, **kwargs):
        # This class allows us to watch for changes in the selected type, so
        #  that we can dynamically change the widget for ``value``.
        self.base_fields['type_controlled'].widget.attrs['class'] = 'attribute_type_controlled'
        super(AttributeInlineForm, self).__init__(*args, **kwargs)


    def full_clean(self):
        super(AttributeInlineForm, self).full_clean()
        if hasattr(self, 'cleaned_data'):
            print 'form', self.cleaned_data



class AttributeInlineFormSet(BaseGenericInlineFormSet):
    def full_clean(self):
        super(AttributeInlineFormSet, self).full_clean()
        if hasattr(self, 'cleaned_data'):
            print 'formset', self.cleaned_data




class AttributeInline(GenericTabularInline):
    model = Attribute
    form = AttributeInlineForm
    formset = generic_inlineformset_factory(Attribute, form=AttributeInlineForm,
                                            formset=AttributeInlineFormSet,
                                            ct_field='source_content_type',
                                            fk_field='source_instance_id')
    extra = 1

    ct_field = 'source_content_type'
    ct_fk_field = 'source_instance_id'

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


class CitationAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'title', 'modified_on_fm', 'modified_by_fm')
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

    readonly_fields = ('uri', 'modified_on_fm','modified_by_fm')

    inlines = (AttributeInline,)

    def save_formset(self, request, form, formset, change):
        return formset.save()

    def save_related(self, request, form, formsets, change):
        """
        Generate a new ``Value`` instance for each ``Attribute``.
        """

        for formset in formsets:
            instances = self.save_formset(request, form, formset, change=change)
            if type(formset).__name__ == 'AttributeFormFormSet':
                for attribute, data in zip(instances, formset.cleaned_data):
                    attr_type, value = data['type_controlled'], data['value']
                    value_model = attr_type.value_content_type.model_class()
                    value_instance = value_model(value=value,
                                                 attribute=attribute)
                    value_instance.save()


class AuthorityAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'name', 'type_controlled')
    list_filter = ('type_controlled',)

    fieldsets = [
        (None, {
            'fields': ('uri',
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
                       'administrator_notes',
                       'record_history',
                       'modified_by_fm',
                       'modified_on_fm')
        }),
    ]
    readonly_fields = ('uri',
                       'classification_system',
                       'classification_code',
                       'classification_hierarchy',
                       'modified_on_fm',
                       'modified_by_fm')


class ACRelationAdmin(SimpleHistoryAdmin):
    list_display = ('id',
                    'authority',
                    'type_controlled',
                    'citation')

    fieldsets = [
        (None, {
            'fields': ('uri',
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
                       'citation',
                       'authority',
                       'modified_by_fm',
                       'modified_on_fm')

class AttributeAdmin(SimpleHistoryAdmin):
    readonly_fields = ('uri', 'value')

admin.site.register(Citation, CitationAdmin)
admin.site.register(Attribute, AttributeAdmin)
admin.site.register(Authority, AuthorityAdmin)
admin.site.register(ACRelation, ACRelationAdmin)
admin.site.register(CCRelation, SimpleHistoryAdmin)
admin.site.register(LinkedData, SimpleHistoryAdmin)
admin.site.register(PartDetails, SimpleHistoryAdmin)
admin.site.register(AARelation, SimpleHistoryAdmin)
admin.site.register(AttributeType)
# Register your models here.
