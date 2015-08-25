from django.contrib import admin
from isisdata.models import *
from simple_history.admin import SimpleHistoryAdmin

class CitationAdmin(SimpleHistoryAdmin):
    list_display = ('title', 'modified_on', 'modified_by', 'created_on', 'created_by')

admin.site.register(Citation, CitationAdmin)
admin.site.register(Attribute, SimpleHistoryAdmin)
admin.site.register(Authority, SimpleHistoryAdmin)
admin.site.register(ACRelation, SimpleHistoryAdmin)
admin.site.register(CCRelation, SimpleHistoryAdmin)
admin.site.register(LinkedData, SimpleHistoryAdmin)
admin.site.register(PartDetails, SimpleHistoryAdmin)
admin.site.register(AARelation, SimpleHistoryAdmin)
# Register your models here.
