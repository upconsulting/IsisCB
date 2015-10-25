from django.conf import settings
from rest_framework.metadata import SimpleMetadata

class CCMetadata(SimpleMetadata):

    def determine_metadata(self, request, view):
        metadata = super(CCMetadata, self).determine_metadata(request, view)
        metadata['license'] = settings.LICENSE
        return metadata
