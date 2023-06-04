from __future__ import unicode_literals
from haystack.backends.elasticsearch_backend import ElasticsearchSearchBackend, ElasticsearchSearchEngine, ElasticsearchSearchQuery
from haystack.utils import get_identifier, get_model_ct
from haystack.constants import DJANGO_CT
import six
import requests, elasticsearch
from django.conf import settings


class IsisCBElasticsearchSearchQuery(ElasticsearchSearchQuery):
    def clean(self, query_fragment):
        """
        Provides a mechanism for sanitizing user input before presenting the
        value to the backend.
        A basic (override-able) implementation is provided.
        """
        if not isinstance(query_fragment, six.string_types):
            return query_fragment

        words = query_fragment.split()
        cleaned_words = []
        for word in words:
            if word in self.backend.RESERVED_WORDS:
                word = word.replace(word, word.lower())

            for char in self.backend.RESERVED_CHARACTERS:
                word = word.replace(char, '\\%s' % char)

            cleaned_words.append(word)

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

    def _get_doc_type_option(self):
        return {
            "doc_type": "modelresult",
        }
        
    def more_like_this(
        self,
        model_instance,
        additional_query_string=None,
        start_offset=0,
        end_offset=None,
        models=None,
        limit_to_registered_models=None,
        result_class=None,
        **kwargs
    ):
        from haystack import connections

        if not self.setup_complete:
            self.setup()

        # Deferred models will have a different class ("RealClass_Deferred_fieldname")
        # which won't be in our registry:
        model_klass = model_instance._meta.concrete_model

        index = (
            connections[self.connection_alias]
            .get_unified_index()
            .get_index(model_klass)
        )
        field_name = index.get_content_field()
        params = {}

        if start_offset is not None:
            params["from_"] = start_offset

        if end_offset is not None:
            params["size"] = end_offset - start_offset

        doc_id = get_identifier(model_instance)

        try:
            # More like this Query
            # https://www.elastic.co/guide/en/elasticsearch/reference/2.2/query-dsl-mlt-query.html
            mlt_query = {
                "query": {
                    "more_like_this": {
                        "fields": [field_name],
                        "docs" : [{"_index" : self.index_name, "_id" : doc_id}],
                    }
                }
            }

            narrow_queries = []

            if additional_query_string and additional_query_string != "*:*":
                additional_filter = {
                    "query": {"query_string": {"query": additional_query_string}}
                }
                narrow_queries.append(additional_filter)

            if limit_to_registered_models is None:
                limit_to_registered_models = getattr(
                    settings, "HAYSTACK_LIMIT_TO_REGISTERED_MODELS", True
                )

            if models and len(models):
                model_choices = sorted(get_model_ct(model) for model in models)
            elif limit_to_registered_models:
                # Using narrow queries, limit the results to only models handled
                # with the current routers.
                model_choices = self.build_models_list()
            else:
                model_choices = []

            if len(model_choices) > 0:
                model_filter = {"terms": {DJANGO_CT: model_choices}}
                narrow_queries.append(model_filter)

            if len(narrow_queries) > 0:
                mlt_query = {
                    "query": {
                        "filtered": {
                            "query": mlt_query["query"],
                            "filter": {"bool": {"must": list(narrow_queries)}},
                        }
                    }
                }

            raw_results = self.conn.search(
                body=mlt_query,
                index=self.index_name,
                _source=True,
                **self._get_doc_type_option(),
                **params,
            )
        except elasticsearch.TransportError as e:
            if not self.silently_fail:
                raise

            self.log.error(
                "Failed to fetch More Like This from Elasticsearch for document '%s': %s",
                doc_id,
                e,
                exc_info=True,
            )
            raw_results = {}

        return self._process_results(raw_results, result_class=result_class)

class IsisCBElasticsearchSearchEngine(ElasticsearchSearchEngine):
    backend = IsisCBElasticsearchSearchBackend
    query = IsisCBElasticsearchSearchQuery
