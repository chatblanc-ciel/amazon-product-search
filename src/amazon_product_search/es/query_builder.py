from typing import Any


def build_multimatch_search_query(query: str, fields: list[str]) -> dict[str, Any]:
    """Build a multimatch ES query.

    Returns:
        dict[str, Any]: The constructed ES query.
    """
    if not query:
        return {
            "match_all": {},
        }

    return {
        "multi_match": {
            "query": query,
            "fields": fields,
            "operator": "or",
        }
    }


def build_knn_search_query(query_vector: list[float], top_k: int) -> dict[str, Any]:
    """Build a KNN ES query from given conditions.

    Args:
        query_vector (list[float]): An encoded query vector.
        top_k (int): A number specifying how many results to return.

    Returns:
        dict[str, Any]: The constructed ES query.
    """
    return {
        "field": "product_vector",
        "query_vector": query_vector,
        "k": top_k,
        "num_candidates": 100,
    }
