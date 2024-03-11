import json
from typing import Any, cast

from amazon_product_search.constants import DATA_DIR, HF, PROJECT_DIR
from amazon_product_search.core.cache import weak_lru_cache
from amazon_product_search.core.es.templates.template_loader import TemplateLoader
from amazon_product_search.core.nlp.tokenizers import Tokenizer, locale_to_tokenizer
from amazon_product_search.core.retrieval.query_vector_cache import QueryVectorCache
from amazon_product_search.core.source import Locale
from amazon_product_search.core.synonyms.synonym_dict import SynonymDict
from amazon_product_search_dense_retrieval.encoders import SBERTEncoder


def expand_synonyms(token_chain: list[tuple[str, list[str]]], current: list[str], result: list[list[str]]):
    if not token_chain:
        result.append(current)
        return

    token, synonyms = token_chain[0]
    expand_synonyms(token_chain[1:], [*current, token], result)
    if synonyms:
        for synonym in synonyms:
            expand_synonyms(token_chain[1:], [*current, synonym], result)


class QueryBuilder:
    def __init__(
        self,
        locale: Locale,
        data_dir: str = DATA_DIR,
        project_dir: str = PROJECT_DIR,
        hf_model_name: str = HF.JP_SLUKE_MEAN,
        synonym_dict: SynonymDict | None = None,
        vector_cache: QueryVectorCache | None = None,
    ) -> None:
        self.synonym_dict = synonym_dict
        self.locale = locale
        self.tokenizer: Tokenizer = locale_to_tokenizer(locale)
        self.encoder: SBERTEncoder = SBERTEncoder(hf_model_name)
        self.template_loader = TemplateLoader(project_dir)
        if vector_cache is None:
            vector_cache = QueryVectorCache()
        self.vector_cache = vector_cache

    def match_all(self) -> dict[str, Any]:
        es_query_str = self.template_loader.load("match_all.j2").render()
        return json.loads(es_query_str)

    def build_lexical_search_query(
        self,
        query: str,
        fields: list[str],
        weight_dict: dict[str, float] | None = None,
        enable_synonym_expansion: bool | float = False,
        enable_phrase_match_boost: bool = False,
        product_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build a multi-match ES query.

        Args:
            query (str): A query to search.
            fields (list[str]): A list of fields to search.
            weight_dict (dict[str, float]): A dictionary specifying the weight of each field.
            enable_synonym_expansion: Expand the given query if True.
            enable_phrase_match_boost: Enable phrase match boosting if True.
            product_ids (list[str], Optional): A list of product IDs to filter.

        Returns:
            dict[str, Any]: The constructed ES query.
        """
        if not query:
            return self.match_all()

        tokens = cast(list, self.tokenizer.tokenize(query))

        if enable_synonym_expansion and self.synonym_dict:
            query_with_synonyms = self.synonym_dict.expand_synonyms(tokens)
            query_tokens: list[list[str]] = []
            expand_synonyms(query_with_synonyms, [], query_tokens)
            queries = [" ".join(tokens) for tokens in query_tokens]
        else:
            queries = [" ".join(tokens)]

        if weight_dict:
            fields = [f"{field}^{weight_dict.get(field, 1)}" for field in fields]

        query_match = json.loads(
            self.template_loader.load("query_match.j2").render(
                queries=queries,
                fields=fields,
                enable_phrase_match_boost=enable_phrase_match_boost,
            )
        )
        if not product_ids:
            return query_match
        return {
            "bool": {
                "must": [
                    query_match,
                ],
                "filter": [
                    {
                        "terms": {
                            "product_id": product_ids,
                        },
                    },
                ],
            },
        }

    @weak_lru_cache(maxsize=128)
    def encode(self, query: str) -> list[float]:
        query_vector = self.vector_cache[query]
        if query_vector is not None:
            return query_vector
        return self.encoder.encode(query).tolist()

    def build_semantic_search_query(
        self,
        query: str,
        field: str,
        top_k: int,
        product_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build a KNN ES query from given conditions.

        Args:
            query (str): A query to encode.
            field (str): A field to examine.
            top_k (int): A number specifying how many results to return.
            product_ids (list[str], Optional): A list of product IDs to filter.

        Returns:
            dict[str, Any]: The constructed ES query.
        """
        query_vector = self.encode(query)
        es_query_str = self.template_loader.load("dense.j2").render(
            query_vector=query_vector,
            field=field,
            k=top_k,
            num_candidates=top_k,
            product_ids=product_ids,
        )
        return json.loads(es_query_str)
