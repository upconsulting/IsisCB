from django.db import models

class Citation(models.Model):
    id = models.CharField(max_length=200)
    title = models.CharField()
    description = models.TextField()
    additional_titles = models.TextField()
    abstract = models.TextField()
    edition_details = models.CharField()
    physical_details = models.CharField()
    language = models.CharField()
    volume = models.CharField()
    # the value for this field should come from a controlled vocabulary
    type_controlled = models.CharField()

    # TBD: here will be a list of association objects

    volume_free_text = models.CharField()
    volume_begin = models.CharField()
    volume_end = models.CharField()
    issue_free_text = models.CharField()
    issue_begin = models.CharField()
    issue_end = models.CharField()
    pages_free_text = models.CharField()
    page_begin = models.CharField()
    page_end = models.CharField()
    extent_note = models.TextField()
    extent = models.CharField()

    notes_on_provenance = models.TextField()
    bibliography_file_source_data = models.CharField()
    notes_on_content_not_published = models.TextField()
    metadata_old_record = models.TextField()
    status_of_record = models.CharField()
    record_action = models.CharField()
    record_locked = models.CharField()
