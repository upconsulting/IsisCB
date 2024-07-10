import haystack
from haystack.backends import BaseEngine

from haystack.backends.elasticsearch7_backend import Elasticsearch7SearchBackend, Elasticsearch7SearchQuery

import logging

logger = logging.getLogger(__name__)

DEFAULT_FIELD_MAPPING = {
    "type": "text",
    "analyzer": "snowball",
}
FIELD_MAPPINGS = {
    "edge_ngram": {
        "type": "text",
        "analyzer": "edgengram_analyzer",
    },
    "ngram": {
        "type": "text",
        "analyzer": "ngram_analyzer",
    },
    "date": {"type": "date"},
    "datetime": {"type": "date"},
    "location": {"type": "geo_point"},
    "boolean": {"type": "boolean"},
    "float": {"type": "float"},
    "long": {"type": "long"},
    "integer": {"type": "long"},
    "object": {"type": "object"}
}


class IsisCBElasticsearch7SearchBackend(Elasticsearch7SearchBackend):
    # Settings to add an n-gram & edge n-gram analyzer.
    DEFAULT_SETTINGS = {
        "settings": {
            "index": {
                "max_ngram_diff": 2,
            },
            "analysis": {
                "analyzer": {
                    "ngram_analyzer": {
                        "tokenizer": "standard",
                        "filter": [
                            "haystack_ngram",
                            "lowercase",
                        ],
                    },
                    "edgengram_analyzer": {
                        "tokenizer": "standard",
                        "filter": [
                            "haystack_edgengram",
                            "lowercase",
                        ],
                    },
                },
                "filter": {
                    "haystack_ngram": {
                        "type": "ngram",
                        "min_gram": 3,
                        "max_gram": 4,
                    },
                    "haystack_edgengram": {
                        "type": "edge_ngram",
                        "min_gram": 2,
                        "max_gram": 15,
                    },
                },
            },
        },
    }

    
    def build_schema(self, fields):
        content_field_name = ""
        mapping = self._get_common_mapping()

        for _, field_class in fields.items():
            field_mapping = FIELD_MAPPINGS.get(
                field_class.field_type, DEFAULT_FIELD_MAPPING
            ).copy()
            if field_class.boost != 1.0:
                field_mapping["boost"] = field_class.boost

            if field_class.document is True:
                content_field_name = field_class.index_fieldname

            # Do this last to override `text` fields.
            if field_mapping["type"] == "text":
                if field_class.indexed is False or hasattr(field_class, "facet_for"):
                    field_mapping["type"] = "keyword"
                    del field_mapping["analyzer"]

            mapping[field_class.index_fieldname] = field_mapping

        return (content_field_name, mapping)



class IsisCBElasticsearch7SearchEngine(BaseEngine):

    backend = IsisCBElasticsearch7SearchBackend
    query = Elasticsearch7SearchQuery