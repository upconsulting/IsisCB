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

    
