from django.contrib import admin
from django.conf.urls import url, include
from django.http import HttpResponse, HttpResponseForbidden, Http404, HttpResponseRedirect, JsonResponse
from django.template import RequestContext, loader
from django.template.response import TemplateResponse
from django.core.exceptions import ValidationError
from django import forms
from django.core.urlresolvers import reverse
from django.forms import formset_factory
from django.forms.models import modelformset_factory
from django.contrib.contenttypes.models import ContentType

from zotero.models import *
from zotero.parser import read, process
from zotero.suggest import *

from isisdata.admin import CitationForm, AttributeInlineForm, ValueField, ValueWidget

import tempfile


class BulkIngestForm(forms.ModelForm):
    zotero_rdf = forms.FileField()


class AuthorityForm(forms.ModelForm):
    id = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Authority
        exclude = ('uri',
                   'id',    # Prevent unique constraint validation.
                   'classification_system',
                   'classification_code',
                   'classification_hierarchy',
                   'modified_on_fm',
                   'modified_by_fm',
                   'created_on_fm',
                   'created_by_fm',
                   'redirect_to')

    def __init__(self, *args, **kwargs):
        super(AuthorityForm, self).__init__(*args, **kwargs)
        for key in self.fields.keys():    # bootstrappiness.
            if key in ['public']:
                continue
            if key in ['administrator_notes', 'description', 'record_history']:
                self.fields[key].widget.attrs['rows'] = 3
            self.fields[key].widget.attrs['class'] = 'form-control'


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
    """
    Provides a table of :class:`models.DraftCitation` instances, and makes AJAX
    requests to :func:`views.suggest_citation_json` for suggested production
    :class:`models.Citation` instances. The user can select suggested
    ``Citation``s into which the corresponding ``DraftCitation``s will be
    merged.

    See also :meth:`.DraftCitationAdmin.match`\.
    """
    context = dict(
        admin.site.each_context(request),
        draftCitations=queryset.filter(processed=False),
        )

    return TemplateResponse(request, "admin/citation_match.html", context)


def match_authorities(modeladmin, request, queryset):
    context = dict(
        admin.site.each_context(request),
        draftAuthorities=queryset.filter(processed=False),
        )

    return TemplateResponse(request, "admin/authority_match.html", context)


def match(request, draftmodel, choicemodel):
    """
    Load selected draft and production instances based on user selection.

    See :meth:`.DraftCitationAdmin.match` and
    :meth:`.DraftAuthorityAdmin.match`\.
    """
    chosen = []
    for field in request.POST.keys():
        if not field.startswith('suggestions_for'):
            continue
        suggestion_choice_id = request.POST.get(field, None)
        # The "None" selection in the radio field has a value of "-1".
        if not suggestion_choice_id or suggestion_choice_id == '-1':
            continue

        # There's a chance that something went wrong with template
        #  rendering that messed up field names. We'll swallow this,
        #  for now...
        try:
            draftinstance_id = int(field.split('_')[-1])
        except ValueError:
            continue

        draftinstance = draftmodel.objects.get(pk=draftinstance_id)
        suggestion_choice = choicemodel.objects.get(pk=suggestion_choice_id)
        chosen.append((draftinstance, suggestion_choice))
    return chosen


def resolve_update_authority(request):
    """
    Process POST data from merge authority view, and update Authority,
    Attribute, and LinkedData instances.
    """
    # Need these for subject_content_type field on Attribute and LinkedData.
    authority_type = ContentType.objects.get_for_model(Authority)

    AuthorityInlineFormset = formset_factory(AuthorityForm)
    AttributeInlineFormSet = formset_factory(AttributeForm)
    LinkedDataInlineFormSet = formset_factory(LinkedDataForm)

    attribute_formset = AttributeInlineFormSet(request.POST, prefix='attribute')
    linkeddata_formset = LinkedDataInlineFormSet(request.POST, prefix='linkeddata')
    authority_formset = AuthorityInlineFormset(request.POST, prefix='authority')

    if all([attribute_formset.is_valid(),
            linkeddata_formset.is_valid(),
            authority_formset.is_valid()]):

        # Update fields on the target Authority instances.
        for authority_data in authority_formset.cleaned_data:
            instance = Authority.objects.get(pk=authority_data['id'])
            del authority_data['id']
            for k, v in authority_data.iteritems():
                setattr(instance, k, v)
            instance.save()

        # Create or update LinkedData entries.
        for datum in linkeddata_formset.cleaned_data:
            if len(datum) == 0:   # Empty form.
                continue

            # LinkedData.subject is a generic relation.
            datum['subject_content_type'] = authority_type
            if not datum['id']:    # New LinkedData instance.
                instance = LinkedData(**datum)
            else:   # Update existing LinkedData instance.
                instance = LinkedData.objects.get(pk=datum['id'])
                for field, value in datum.iteritems():
                    setattr(instance, field, value)
            instance.save()

        # Create or update Attributes.
        for datum in attribute_formset.cleaned_data:
            if len(datum) == 0:   # Empty form.
                continue

            datum['source_content_type'] = authority_type

            # value_content_type is a ContentType instance.
            value_class = datum['type_controlled'].value_content_type.model_class()
            new_value = datum['value']
            del datum['value']
            if not datum['id']:    # New Attribute.
                instance = Attribute(**datum)
                instance.save()
                value_instance = value_class(value=value, attribute=instance)
            else:                  # Update existing attribute.
                instance = Attribute.objects.get(pk=datum['id'])
                for field, value in datum.iteritems():
                    setattr(instance, field, value)
                value_instance = instance.value
                value_instance.value = new_value
                instance.save()
            value_instance.save()


def resolve(request, draftmodel, choicemodel):
    """
    Perform a draft -> production merge for all instances indicated by the
    user. See :meth:`.DraftCitationAdmin.resolve` and
    :meth:`.DraftAuthorityAdmin.resolve`\.
    """
    if draftmodel is DraftAuthority:
        # We're doing this the hard way, and "manually" handling the cleaned
        #  form data.
        resolve_update_authority(request)

    for field in request.POST.keys():
        if not field.startswith('merge'):
            continue

        draftinstance_id = int(field.split('_')[-1])
        choice_id = request.POST.get(field, None)

        draftinstance = draftmodel.objects.get(pk=draftinstance_id)

        if draftinstance.processed:
            continue
        choice_instance = choicemodel.objects.get(pk=choice_id)

        irEvent = InstanceResolutionEvent(
            for_instance=draftinstance,
            to_instance=choice_instance,
        )
        irEvent.save()

        draftinstance.processed = True
        draftinstance.save()


class DraftCitationAdmin(admin.ModelAdmin):
    class Meta:
        model = DraftCitation

    list_display = ('title', 'imported_on', 'processed')
    inlines = []
    # list_filter = ('processed',)

    actions = [match_citations]

    def get_queryset(self, *args, **kwargs):
        """
        Processed records are hidden.
        """
        queryset = super(DraftCitationAdmin, self).get_queryset(*args, **kwargs)
        return queryset.filter(processed=False)

    def find_matches(self, request, draftcitation_id):
        """
        We serve the match_citations action as a view here so that we can
        use reverse resolution in templates.
        """
        return match_citations(self, request, DraftCitation.objects.filter(id=int(draftcitation_id)))

    def create_citation(self, request, draftcitation_id):
        """
        TODO: implement.
        """
        return

    def match(self, request):
        """
        The match_citations admin action will route POST data here. If the user
        has selected citations to merge, we display a confirmation page.
        Otherwise, we just redirect the user back to the changelist view.
        """

        context = dict(self.admin_site.each_context(request))
        if request.method == 'POST':
            chosen = match(request, DraftCitation, Citation)

            # The user may not have chosen any production citations, in which
            #  case we simply return to the changelist.
            if len(chosen) > 0:
                context.update({'chosen_suggestions': chosen})
                # But if they did choose production citations, we want to
                #  confirm that they wish to proceed with the merge action.
                return TemplateResponse(request, "admin/citation_match_do.html", context)

        # Non-POST requests should take the user back to the changelist.
        return HttpResponseRedirect(reverse('admin:zotero_draftcitation_changelist'))

    def resolve(self, request):
        """
        The :meth:`.match` view will route POST data here. The user has
        confirmed that they want to merge the selected citations.
        """

        if request.method == 'POST':
            resolve(request, DraftCitation, Citation)

        # Back to the changelist!
        return HttpResponseRedirect(reverse('admin:zotero_draftcitation_changelist'))


    def get_urls(self):
        urls = super(DraftCitationAdmin, self).get_urls()
        extra_urls = [
            url(r'^create_citation/(?P<draftcitation_id>[0-9]+)/$', self.admin_site.admin_view(self.create_citation), name="draftcitation_create_citation"),
            url(r'^findmatches/(?P<draftcitation_id>[0-9]+)/$', self.admin_site.admin_view(self.find_matches), name="draftcitation_findmatches"),
            url(r'^match/$', self.admin_site.admin_view(self.match), name="draftcitation_match"),
            url(r'^resolve/$', self.admin_site.admin_view(self.resolve), name="draftcitation_resolve"),
        ]
        return extra_urls + urls


class LinkedDataForm(forms.ModelForm):
    id = forms.CharField(widget=forms.HiddenInput(), required=False)
    subject_content_type = forms.CharField(widget=forms.HiddenInput(), required=False)
    subject_instance_id = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = LinkedData
        fields = ['type_controlled', 'universal_resource_name']

    def __init__(self, *args, **kwargs):
        super(LinkedDataForm, self).__init__(*args, **kwargs)
        for key in self.fields.keys():
            self.fields[key].required = False
            self.fields[key].widget.attrs['class'] = 'form-control'



class AttributeForm(forms.ModelForm):
    value = forms.CharField(required=False)
    id = forms.CharField(widget=forms.HiddenInput(), required=False)
    source_content_type = forms.CharField(widget=forms.HiddenInput(), required=False)
    source_instance_id = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Attribute
        fields = ['type_controlled', 'value_freeform',]

    def __init__(self, *args, **kwargs):
        super(AttributeForm, self).__init__(*args, **kwargs)
        for key in self.fields.keys():
            self.fields[key].required = False
            self.fields[key].widget.attrs['class'] = 'form-control'

    def is_valid(self):
        """
        Enforce validation for ``value`` based on ``type_controlled``.
        """
        val = super(AttributeForm, self).is_valid()

        if all(x in self.cleaned_data for x in ['value', 'type_controlled']):
            value = self.cleaned_data['value']
            attr_type = self.cleaned_data['type_controlled']
            if (value and not attr_type) or (attr_type and not value):
                self.add_error('value', 'Missing data')
            value_model = attr_type.value_content_type.model_class()
            try:
                value_model.is_valid(value)
            except ValidationError as E:
                self.add_error('value', E)
        return super(AttributeForm, self).is_valid()


class DraftAuthorityAdmin(admin.ModelAdmin):
    list_display = ('name', 'imported_on', 'processed')
    # list_filter = ('processed', )

    actions = [match_authorities]
    inlines = []

    def get_queryset(self, *args, **kwargs):
        """
        Processed records are hidden.
        """
        queryset = super(DraftAuthorityAdmin, self).get_queryset(*args, **kwargs)
        return queryset.filter(processed=False)

    def find_matches(self, request, draftauthority_id):
        """
        We serve the match_authorities action as a view here so that we can
        use reverse resolution in templates.
        """
        return match_authorities(self, request, DraftAuthority.objects.filter(id=int(draftauthority_id)))

    def match(self, request):
        """
        The match_citations admin action will route POST data here. If the user
        has selected citations to merge, we display a confirmation page.
        Otherwise, we just redirect the user back to the changelist view.
        """

        context = dict(self.admin_site.each_context(request))
        if request.method == 'POST':
            chosen = match(request, DraftAuthority, Authority)

            # The user may not have chosen any production authority records, in
            #  which case we simply return to the changelist.
            if len(chosen) > 0:
                authority_type = ContentType.objects.get_for_model(Authority)

                AuthorityInlineFormset = formset_factory(AuthorityForm, extra=0)
                AttributeInlineFormSet = formset_factory(AttributeForm, extra=1)
                LinkedDataInlineFormSet = formset_factory(LinkedDataForm, extra=1)

                # Generate initial data for formsets.
                initial_attribute = []
                initial_linkeddata = []
                initial_attribute_groups = []    # Associates forms in formset
                initial_linkeddata_groups = []   #  with choices.
                a, l = 0, 0
                for draftauthority, authority in chosen:
                    attribute_group = []
                    linkeddata_group = []
                    for attribute in authority.attributes.all():
                        attribute_group.append(a)
                        initial_attribute.append({
                            'id': attribute.id,
                            'value': attribute.value.get_child_class().value,
                            'type_controlled': attribute.type_controlled,
                            'value_freeform': attribute.value_freeform,
                            'source_content_type': authority_type.id,
                            'source_instance_id': authority.id,
                        })
                        a += 1

                    for linkeddata in authority.linkeddata_entries.all():

                        linkeddata_group.append(l)
                        initial_linkeddata.append({
                            'id': linkeddata.id,
                            'universal_resource_name': linkeddata.universal_resource_name,
                            'type_controlled': linkeddata.type_controlled,
                            'subject_content_type': authority_type.id,
                            'subject_instance_id': authority.id,
                        })
                        l += 1
                    initial_attribute_groups.append(attribute_group)
                    initial_linkeddata_groups.append(linkeddata_group)

                # Generate formsets using the initial data generated above.
                attribute_formset = AttributeInlineFormSet(prefix='attribute', initial=initial_attribute)
                linkeddata_formset = LinkedDataInlineFormSet(prefix='linkeddata', initial=initial_linkeddata)

                # Sort the formsets out into groups based on the Authority to
                #  which they correspond.
                attribute_forms = [[attribute_formset[i] for i in group] for group in initial_attribute_groups]
                linkeddata_forms = [[linkeddata_formset[i] for i in group] for group in initial_linkeddata_groups]

                # Formset for the Authority records themselves.
                formset = AuthorityInlineFormset(prefix='authority', initial=[
                    {
                        'id': authority.id,
                        'name': authority.name,
                        'type_controlled': authority.type_controlled,
                        'description': authority.description,
                        'record_status': authority.record_status,
                        'record_history': authority.record_history,
                        'administrator_notes': authority.administrator_notes,
                        'public': authority.public,
                    }
                    for draftauthority, authority in chosen])

                # Here we stitch together the formsets so that each
                #  DraftAuthority is grouped together whith its corresponding
                #  Authority (into which it will be merged), the Authority's
                #  pre-filled form, and the Authority's share of the
                #  LinkedData and Attribute formsets. This way we can separate
                #  all of these bits out according to DraftAuthority/Authority
                #  pairs in the template.
                chosen = zip(zip(*chosen)[0], zip(*chosen)[1], formset, attribute_forms, linkeddata_forms)

                context.update({
                    'chosen_suggestions': chosen,
                    'authority_formset': formset,
                    'linkeddata_formset': linkeddata_formset,
                    'attribute_formset': attribute_formset,
                    'attribute_template_form': attribute_formset[-1],
                    'linkeddata_template_form': linkeddata_formset[-1],
                })
                # But if they did choose production authority records, we want
                #  to confirm that they wish to proceed with the merge action.
                return TemplateResponse(request, "admin/authority_match_do.html", context)

        # Non-POST requests should take the user back to the changelist.
        return HttpResponseRedirect(reverse('admin:zotero_draftauthority_changelist'))

    def resolve(self, request):
        """
        The :meth:`.match` view will route POST data here. The user has
        confirmed that they want to merge the selected citations.
        """

        if request.method == 'POST':
            resolve(request, DraftAuthority, Authority)

        # Back to the changelist!
        return HttpResponseRedirect(reverse('admin:zotero_draftauthority_changelist'))

    def create_authority(self, request, draftauthority_id):
        """
        A staff user can create a new :class:`isisdata.Authority` record using
        data from a :class:`zotero.DraftAuthority` instance.
        """
        context = dict(self.admin_site.each_context(request))
        draftauthority = DraftAuthority.objects.get(pk=draftauthority_id)
        context.update({'draftauthority': draftauthority})

        AttributeInlineFormSet = formset_factory(AttributeForm)
        LinkedDataInlineFormSet = formset_factory(LinkedDataForm)

        if request.method == 'GET':
            form = AuthorityForm(initial={
                'name': draftauthority.name,
                'type_controlled': draftauthority.type_controlled,
                'record_history': u'Created from Zotero accession {0}, performed at {1} by {2}. Subsequently validated and curated by {3}.'.format(draftauthority.part_of.id, draftauthority.part_of.imported_on, draftauthority.part_of.imported_by, request.user.username),
                })
            attributeFormset = AttributeInlineFormSet()
            linkeddataFormset = LinkedDataInlineFormSet()


        elif request.method == 'POST':
            form = AuthorityForm(request.POST)
            attributeFormset = AttributeInlineFormSet(request.POST)
            linkeddataFormset = LinkedDataInlineFormSet(request.POST)

            if form.is_valid() and attributeFormset.is_valid() and linkeddataFormset.is_valid():
                # Create the Authority entry.
                instance = form.save()

                # Create new Attributes.
                for attributeForm in attributeFormset:
                    attributeType = attributeForm.cleaned_data['type_controlled']
                    valueModel = attributeType.value_content_type.model_class()
                    value = attributeForm.cleaned_data['value']

                    attribute_instance = Attribute(
                        source=instance,
                        type_controlled=attributeType,
                    )
                    attribute_instance.save()
                    value_instance = valueModel(
                        attribute=attribute_instance,
                        value=value,
                    )
                    value_instance.save()

                # Create new LinkedData entries.
                for linkeddataForm in linkeddataFormset:
                    linkeddataType = linkeddataForm.cleaned_data['type_controlled']
                    urn = linkeddataForm.cleaned_data['universal_resource_name']
                    linkeddata_instance = LinkedData(
                        subject=instance,
                        universal_resource_name=urn,
                        type_controlled=linkeddataType,
                    )
                    linkeddata_instance.save()

                # Add a new InstanceResolutionEvent.
                irEvent = InstanceResolutionEvent(
                    for_instance=draftauthority,
                    to_instance=instance
                )
                irEvent.save()

                # Update the DraftAuthority.
                draftauthority.processed = True
                draftauthority.save()

                # If successful, take the user to the Authority change view.
                return HttpResponseRedirect(reverse("admin:isisdata_authority_change", args=[instance.id]))

        context.update({
            'form': form,
            'attribute_formset': attributeFormset,
            'linkeddata_formset': linkeddataFormset,
            })
        return TemplateResponse(request, "admin/authority_create.html", context)


    def get_urls(self):
        urls = super(DraftAuthorityAdmin, self).get_urls()
        extra_urls = [
            url(r'^create_authority/(?P<draftauthority_id>[0-9]+)/$', self.admin_site.admin_view(self.create_authority), name="draftauthority_create_authority"),
            url(r'^findmatches/(?P<draftauthority_id>[0-9]+)/$', self.admin_site.admin_view(self.find_matches), name="draftauthority_findmatches"),
            url(r'^match/$', self.admin_site.admin_view(self.match), name="draftauthority_match"),
            url(r'^resolve/$', self.admin_site.admin_view(self.resolve), name="draftauthority_resolve"),
        ]
        return extra_urls + urls


# Register your models here.
admin.site.register(DraftCitation, DraftCitationAdmin)
admin.site.register(DraftAuthority, DraftAuthorityAdmin)
admin.site.register(ImportAccession, ImportAccessionAdmin)
admin.site.register(DraftACRelation)
admin.site.register(DraftAttribute)
admin.site.register(DraftCitationLinkedData)
admin.site.register(DraftAuthorityLinkedData)
admin.site.register(InstanceResolutionEvent)
