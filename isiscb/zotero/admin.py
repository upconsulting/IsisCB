from django.contrib import admin
from django.conf.urls import url, include
from django.http import HttpResponse, HttpResponseForbidden, Http404, HttpResponseRedirect, JsonResponse
from django.template import RequestContext, loader
from django.template.response import TemplateResponse
from django.core.exceptions import ValidationError
from django import forms

from zotero.models import *
from zotero.parser import read, process
from zotero.suggest import *

import tempfile


class BulkIngestForm(forms.ModelForm):
    zotero_rdf = forms.FileField()


class ImportAccessionAdmin(admin.ModelAdmin):
    form = BulkIngestForm
    list_display = ('name', 'imported_on')
    readonly_fields = ('imported_by',)
    inlines = []

    def save_model(self, request, obj, form, change):

        obj.imported_by = request.user
        super(ImportAccessionAdmin, self).save_model(request, obj, form, change)
        with tempfile.NamedTemporaryFile(suffix='.rdf', delete=False) as destination:
            destination.write(form.cleaned_data['zotero_rdf'].file.read())
            path = destination.name

        papers = read(path)
        process(papers, instance=form.instance)


def match_citations(modeladmin, request, queryset):
    context = dict(
        admin.site.each_context(request),
        draftCitations=queryset
        )

    return TemplateResponse(request, "admin/citation_match.html", context)


def match_authorities(modeladmin, request, queryset):
    context = dict(
        admin.site.each_context(request),
        draftAuthorities=queryset
        )

    return TemplateResponse(request, "admin/authority_match.html", context)


class DraftCitationAdmin(admin.ModelAdmin):
    class Meta:
        model = DraftCitation

    list_display = ('title', 'imported_on')
    inlines = []

    actions = [match_citations]
    #
    # def match(self, request):
    #     context = dict(self.admin_site.each_context(request))
    #
    #
    #
    # def get_urls(self):
    #     urls = super(DraftCitationAdmin, self).get_urls()
    #     extra_urls = [
    #         url(r'^match/$', self.match),
    #     ]
    #     return extra_urls + urls


class DraftAuthorityAdmin(admin.ModelAdmin):
    list_display = ('name', 'imported_on')
    actions = [match_authorities]
    inlines = []


# Register your models here.
admin.site.register(DraftCitation, DraftCitationAdmin)
admin.site.register(DraftAuthority, DraftAuthorityAdmin)
admin.site.register(ImportAccession, ImportAccessionAdmin)
admin.site.register(DraftACRelation)
admin.site.register(DraftAttribute)
admin.site.register(DraftCitationLinkedData)
