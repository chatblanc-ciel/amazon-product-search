from amazon_product_search.core.es.es_client import EsClient
from amazon_product_search.core.es.query_builder import QueryBuilder
from amazon_product_search.core.es.response import Response
from amazon_product_search.core.nlp.normalizer import normalize_query
from amazon_product_search.core.retrieval.rank_fusion import RankFusion, fuse
from amazon_product_search.core.source import Locale


def split_fields(fields: list[str]) -> tuple[list[str], list[str]]:
    """Convert a given list of fields into a tuple of (sparse_fields, dense_fields)

    Field names containing "vector" will be considered dense_fields.

    Args:
        fields (list[str]): A list of fields.

    Returns:
        tuple[list[str], list[str]]: A tuple of (sparse_fields, dense_fields)
    """
    sparse_fields: list[str] = []
    dense_fields: list[str] = []
    for field in fields:
        (dense_fields if "vector" in field else sparse_fields).append(field)
    return sparse_fields, dense_fields


class Retriever:
    def __init__(
        self, locale: Locale, es_client: EsClient | None = None, query_builder: QueryBuilder | None = None
    ) -> None:
        if es_client:
            self.es_client = es_client
        else:
            self.es_client = EsClient()

        if query_builder:
            self.query_builder = query_builder
        else:
            self.query_builder = QueryBuilder(locale)

    def search(
        self,
        index_name: str,
        query: str,
        fields: list[str],
        is_synonym_expansion_enabled: bool = False,
        query_type: str = "combined_fields",
        product_ids: list[str] | None = None,
        sparse_boost: float = 1.0,
        dense_boost: float = 1.0,
        size: int = 20,
        rank_fusion: RankFusion | None = None,
    ) -> Response:
        normalized_query = normalize_query(query)
        sparse_fields, dense_fields = split_fields(fields)
        sparse_query = None
        if sparse_fields:
            sparse_query = self.query_builder.build_sparse_search_query(
                query=normalized_query,
                fields=sparse_fields,
                query_type=query_type,
                boost=sparse_boost,
                is_synonym_expansion_enabled=is_synonym_expansion_enabled,
                product_ids=product_ids,
            )
        dense_query = None
        if normalized_query and dense_fields:
            dense_query = self.query_builder.build_dense_search_query(
                normalized_query,
                field=dense_fields[0],
                top_k=size,
                boost=dense_boost,
                product_ids=product_ids,
            )

        if not rank_fusion:
            rank_fusion = RankFusion()

        if rank_fusion.fuser == "search_engine":
            return self.es_client.search(
                index_name=index_name,
                query=sparse_query,
                knn_query=dense_query,
                size=size,
                explain=True,
            )

        sparse_response = self.es_client.search(
            index_name=index_name,
            query=sparse_query,
            knn_query=None,
            size=size,
            explain=True,
        )
        dense_response = self.es_client.search(
            index_name=index_name,
            query=None,
            knn_query=dense_query,
            size=size,
            explain=True,
        )
        return fuse(query, sparse_response, dense_response, sparse_boost, dense_boost, rank_fusion, size)
