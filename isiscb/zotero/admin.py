from django.contrib import admin
from django.conf.urls import url, include
from django.http import HttpResponse, HttpResponseForbidden, Http404, HttpResponseRedirect, JsonResponse
from django.template import RequestContext, loader
from django.core.exceptions import ValidationError
from django import forms

from zotero.models import *
from zotero.parser import read, process
import tempfile


class BulkIngestForm(forms.ModelForm):
    zotero_rdf = forms.FileField()




class ImportAccessionAdmin(admin.ModelAdmin):
    form = BulkIngestForm
    list_display = ('name', 'imported_on')

    def save_model(self, request, obj, form, change):
        super(ImportAccessionAdmin, self).save_model(request, obj, form, change)
        with tempfile.NamedTemporaryFile(suffix='.rdf', delete=False) as destination:
            destination.write(form.cleaned_data['zotero_rdf'].file.read())
            path = destination.name

        papers = read(path)
        process(papers, instance=form.instance)


class DraftCitationAdmin(admin.ModelAdmin):
    class Meta:
        model = DraftCitation

    list_display = ('title', 'imported_on')

    def bulk_ingest(self, request):
        template = loader.get_template('admin/bulk_ingest.html')
        context = RequestContext(request, {})
        return HttpResponse(template.render(context))


    def get_urls(self):
        urls = super(DraftCitationAdmin, self).get_urls()
        extra_urls = [
            url(r'^bulk/$', self.bulk_ingest),
        ]
        return extra_urls + urls


# Register your models here.
admin.site.register(DraftCitation, DraftCitationAdmin)
admin.site.register(DraftAuthority)
admin.site.register(ImportAccession, ImportAccessionAdmin)
admin.site.register(DraftACRelation)
admin.site.register(DraftAttribute)
