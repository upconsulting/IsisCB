import datetime
from haystack import indexes
from django.forms import MultiValueField
from isisdata.models import Citation


class CitationIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(model_attr='title', null=True)
    description = indexes.CharField(model_attr='description', null=True)
    abstract = indexes.CharField(model_attr='abstract', null=True)
    edition_details = indexes.CharField(model_attr='edition_details', null=True)
    physical_details = indexes.CharField(model_attr='physical_details', null=True)
    attributes = MultiValueField()

    def get_model(self):
        return Citation

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.filter()

#site.register(Citation, CitationIndex)
