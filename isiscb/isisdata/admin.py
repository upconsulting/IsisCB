from django.contrib import admin
from django import forms
from isisdata.models import *
from simple_history.admin import SimpleHistoryAdmin

# TODO: The Choice widget cannot handle this many choices. Consider using an
#  autocomplete, or some other widget that loads ``object`` choices dynamically
#  via AJAX.
class CCRelationForm(forms.ModelForm):
    class Meta:
        model = CCRelation
        fields = ('object', )

    object = forms.ChoiceField(required=True, choices=CCRelation.objects.values_list('id', 'name'))


class CCRelationInline(admin.TabularInline):
    fk_name = 'subject'
    model = CCRelation
    form = CCRelationForm
    extra = 1


class CitationAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'title', 'modified_on_fm', 'modified_by_fm')
    fieldsets = [
        (None, {'fields': ('uri', 'title', 'description', 'language',
                           'type_controlled')}),
        ('Additional Details', {'fields': ('abstract', 'edition_details',
                                           'physical_details')}),
        ('Curation', {'fields': ('record_action', 'status_of_record',
                                 'administrator_notes', 'record_history',
                                 'modified_by_fm', 'modified_on_fm')}),
    ]

    readonly_fields = ('uri', 'modified_on_fm','modified_by_fm')




class AuthorityAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'name', 'type_controlled')
    list_filter = ('type_controlled',)

    fieldsets = [
        (None, {'fields': ('uri', 'name', 'description', 'type_controlled')}),
        ('Classification', {'fields': ('classification_system',
                                       'classification_code',
                                       'classification_hierarchy')}),
        ('Curation', {'fields': ('record_status', 'administrator_notes',
                                 'record_history', 'modified_by_fm',
                                 'modified_on_fm')}),
    ]
    readonly_fields = ('uri', 'classification_system', 'classification_code',
                       'classification_hierarchy', 'modified_on_fm',
                       'modified_by_fm')

class ACRelationAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'authority', 'type_controlled', 'citation')
    readonly_fields = ('authority', 'citation')
    fieldsets = [
        (None, {
            'fields': ('uri', 'citation', 'authority', 'name',
                       'name_for_display_in_citation', 'description')
        }),
        ('Type', {
            'fields': ('type_controlled', 'type_broad_controlled','type_free')
        }),
        ('Curation', {
            'fields': ('administrator_notes', 'record_history',
                       'modified_by_fm', 'modified_on_fm')
        }),
    ]
    readonly_fields = ('uri', 'citation', 'authority', 'modified_by_fm',
                       'modified_on_fm')

admin.site.register(Citation, CitationAdmin)
admin.site.register(Attribute, SimpleHistoryAdmin)
admin.site.register(Authority, AuthorityAdmin)
admin.site.register(ACRelation, ACRelationAdmin)
admin.site.register(CCRelation, SimpleHistoryAdmin)
admin.site.register(LinkedData, SimpleHistoryAdmin)
admin.site.register(PartDetails, SimpleHistoryAdmin)
admin.site.register(AARelation, SimpleHistoryAdmin)
# Register your models here.
