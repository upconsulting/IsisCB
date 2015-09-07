import datetime
from haystack import indexes
from django.forms import MultiValueField
from isisdata.models import Citation, Authority


class CitationIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(model_attr='title', null=True)
    description = indexes.CharField(model_attr='description', null=True)
    abstract = indexes.CharField(model_attr='abstract', null=True)
    edition_details = indexes.CharField(model_attr='edition_details', null=True)
    physical_details = indexes.CharField(model_attr='physical_details', null=True)
    attributes = indexes.MultiValueField()
    authorities = indexes.MultiValueField(faceted=True)
    authors = indexes.MultiValueField(faceted=True)
    subjects = indexes.MultiValueField(faceted=True)
    persons = indexes.MultiValueField(faceted=True)
    categories = indexes.MultiValueField(faceted=True)

    def get_model(self):
        return Citation

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.all()

    def prepare_authorities(self, obj):
        # Store a list of id's for filtering
        return [acrel.authority.name for acrel in obj.acrelation_set.all()]

    def prepare_attributes(self, obj):
        return [attr.value_freeform for attr in obj.attributes.all()]

    def prepare_authors(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(type_controlled__in=['AU', 'CO'])]

    def prepare_subjects(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(type_controlled__in=['SU'])]

    def prepare_persons(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(type_controlled__in=['PR'])]

    def prepare_categories(self, obj):
        return [acrel.authority.name for acrel in obj.acrelation_set.filter(type_controlled__in=['CA'])]

class AuthorityIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(model_attr='name')
    description = indexes.CharField(model_attr='description', null=True)
    attributes = indexes.MultiValueField()


    def get_model(self):
        return Authority

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.all()

    def prepare_attributes(self, obj):
        return [attr.value_freeform for attr in obj.attributes.all()]
