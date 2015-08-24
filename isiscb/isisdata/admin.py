from django.contrib import admin
from isisdata.models import *
from simple_history.admin import SimpleHistoryAdmin

class CitationAdmin(SimpleHistoryAdmin):
    list_display = ('title', 'modified_on', 'modified_by', 'created_on', 'created_by')

admin.site.register(Citation, CitationAdmin)
admin.site.register(Attribute, SimpleHistoryAdmin)
# Register your models here.
