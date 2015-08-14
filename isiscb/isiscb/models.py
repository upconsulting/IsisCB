from django.db import models

class Citation(models.Model):
    id = models.CharField(max_length=200, primary_key=True)
    title = models.CharField()
    description = models.TextField()
    additional_titles = models.TextField()
    abstract = models.TextField()
    edition_details = models.CharField()
    physical_details = models.CharField()
    language = models.CharField()
    volume = models.CharField()
    url = models.URLField()

    # the value for this field should come from a controlled vocabulary
    type_controlled = models.CharField()

    # TBD: here will be a list of association objects
    author_editor = models.ManyToManyField(Authority, through='ACRelation')

    volume_free_text = models.CharField()
    volume_begin = models.IntegerField()
    volume_end = models.IntegerField()
    issue_free_text = models.CharField()
    issue_begin = models.IntegerField()
    issue_end = models.IntegerField()
    pages_free_text = models.CharField()
    page_begin = models.IntegerField()
    page_end = models.IntegerField()

    # Numerical measure of the extent of the resource such as the number of pages or number of words
    # Should this also contain works (E.g. 'pages', 'words')?
    extent_note = models.TextField()
    extent = models.CharField()

    notes_on_provenance = models.TextField()
    bibliography_file_source_data = models.CharField()
    notes_on_content_not_published = models.TextField()
    metadata_old_record = models.TextField()
    status_of_record = models.CharField()
    record_action = models.CharField()
    record_locked = models.CharField()

    #the following fields are in orange in FM db; why? maybe old data?


    # admin fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField()
    modified_on = models.DateTimeField(auto_now=True)
    modified_by = models.CharField()

class Authority(models.Model):
    id = models.CharField(max_length=200, primary_key=True)
    name = models.Charfield()

class ACRelation(models.Model):
    id = models.CharField(max_length=200, primary_key=True)
    citation = models.ForeignKey(Citation)
    authority = models.ForeignKey(Authority)
