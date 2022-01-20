from __future__ import unicode_literals
from haystack.backends.elasticsearch_backend import ElasticsearchSearchBackend, ElasticsearchSearchEngine, ElasticsearchSearchQuery
import six


class IsisCBElasticsearchSearchQuery(ElasticsearchSearchQuery):
    def clean(self, query_fragment):
        """
        Provides a mechanism for sanitizing user input before presenting the
        value to the backend.
        A basic (override-able) implementation is provided.
        """
        # print query_fragment
        if not isinstance(query_fragment, six.string_types):
            return query_fragment

        words = query_fragment.split()
        cleaned_words = []
        # print words
        for word in words:
            if word in self.backend.RESERVED_WORDS:
                word = word.replace(word, word.lower())

            for char in self.backend.RESERVED_CHARACTERS:
                word = word.replace(char, '\\%s' % char)

            cleaned_words.append(word)
        # print cleaned_words

        return ' '.join(cleaned_words)


class IsisCBElasticsearchSearchBackend(ElasticsearchSearchBackend):
    RESERVED_CHARACTERS = (
        '\\', '+', '-', '&&', '||', '!', '(', ')', '{', '}',
        '[', ']', '^', '"', '~',  ':', '/', #'*', '?',
    )

    DEFAULT_SETTINGS = {
        'settings': {
            "analysis": {
                "analyzer": {
                    "default" : {
                        "tokenizer" : "standard",
                        "filter" : ["standard", "asciifolding"]
                    },
                    "ngram_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["haystack_ngram", "lowercase"]
                    },
                    "edgengram_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["haystack_edgengram", "lowercase", "asciifolding"]
                    }
                },
                "tokenizer": {
                    "haystack_ngram_tokenizer": {
                        "type": "nGram",
                        "min_gram": 3,
                        "max_gram": 15,
                    },
                    "haystack_edgengram_tokenizer": {
                        "type": "edgeNGram",
                        "min_gram": 3,
                        "max_gram": 15,
                        "side": "front"
                    }
                },
                "filter": {
                    "haystack_ngram": {
                        "type": "nGram",
                        "min_gram": 3,
                        "max_gram": 15
                    },
                    "haystack_edgengram": {
                        "type": "edgeNGram",
                        "min_gram": 3,
                        "max_gram": 15
                    }
                }
            }
        }
    }

    def build_schema(self, fields):
        content_field_name, mapping = super(
            IsisCBElasticsearchSearchBackend, self
        ).build_schema(
            fields
        )

        for field_name, field_class in fields.items():
            field_mapping = mapping[field_class.index_fieldname]
            if field_class.field_type == "object":
                mapping[field_class.index_fieldname] = {"type": "object"}

        return (content_field_name, mapping)

class IsisCBElasticsearchSearchEngine(ElasticsearchSearchEngine):
    backend = IsisCBElasticsearchSearchBackend
    query = IsisCBElasticsearchSearchQuery
