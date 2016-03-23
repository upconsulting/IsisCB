from django.contrib import admin
from openurl.models import *


class CuratedAdminMixin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        """
        Set the current user as creator.
        """

        try:
            obj.added_by
        except:
            obj.added_by = request.user
        obj.save()


class ResolverInline(admin.StackedInline):
    fk_name = 'belongs_to'
    model = Resolver
    extra = 0
    exclude = ['added_by']


class InstitutionAdmin(CuratedAdminMixin):
    class Meta:
        model = Institution
    exclude = ['added_by']

    inlines = [ResolverInline]

    def save_formset(self, request, form, formset, change):
        """
        Set the current user as creator.
        """
        formset.save(commit=False)
        for f in formset.forms:
            obj = f.instance
            try:
                obj.added_by
            except:
                obj.added_by = request.user
            obj.save()


class ResolverAdmin(CuratedAdminMixin):
    class Meta:
        model = Resolver
    exclude = ['added_by']


admin.site.register(Institution, InstitutionAdmin)
