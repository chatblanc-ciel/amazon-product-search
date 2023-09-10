from typing import Any, Optional

import streamlit as st

from amazon_product_search.core.es.es_client import EsClient
from amazon_product_search.core.es.query_builder import QueryBuilder
from amazon_product_search.core.metrics import (
    compute_ndcg,
    compute_precision,
    compute_recall,
)
from amazon_product_search.core.reranking.reranker import from_string
from amazon_product_search.core.retrieval.options import DynamicWeighting, FixedWeighting, MatchingMethod
from amazon_product_search.core.retrieval.retriever import Retriever
from demo.apps.search.search_ui import (
    draw_input_form,
    draw_products,
    draw_response_stats,
)
from demo.page_config import set_page_config
from demo.utils import load_merged

es_client = EsClient()
query_builder = QueryBuilder()
retriever = Retriever(es_client, query_builder)


@st.cache_data
def load_dataset() -> dict[str, dict[str, tuple[str, str]]]:
    df = load_merged(locale="jp").to_pandas()
    df = df[df["split"] == "test"]
    query_to_label: dict[str, dict[str, tuple[str, str]]] = {}
    for query, group in df.groupby("query"):
        query_to_label[query] = {}
        for row in group.to_dict("records"):
            query_to_label[query][row["product_id"]] = (
                row["esci_label"],
                row["product_title"],
            )
    return query_to_label


def draw_es_query(query: Optional[dict[str, Any]], knn_query: Optional[dict[str, Any]], size: int) -> None:
    es_query: dict[str, Any] = {
        "size": size,
    }

    if query:
        es_query["query"] = query

    if knn_query:
        es_query["knn"] = knn_query

    st.write("Elasticsearch Query:")
    st.write(es_query)


def main() -> None:
    set_page_config()
    st.write("## Search")

    queries, query_to_label = None, {}
    use_dataset = st.checkbox("Use Dataset:", value=True)
    if use_dataset:
        query_to_label = load_dataset()
        queries = query_to_label.keys()

    st.write("#### Input")
    with st.form("input"):
        form_input = draw_input_form(es_client.list_indices(), queries)
        if not st.form_submit_button("Search"):
            return

    weighting_strategy = (
        FixedWeighting({MatchingMethod.SPARSE: form_input.sparse_boost, MatchingMethod.DENSE: form_input.dense_boost})
        if form_input.weighting_strategy == "fixed"
        else DynamicWeighting()
    )
    response = retriever.search(
        index_name=form_input.index_name,
        query=form_input.query,
        fields=form_input.fields,
        query_type=form_input.query_type,
        is_synonym_expansion_enabled=form_input.is_synonym_expansion_enabled,
        sparse_boost=form_input.sparse_boost,
        dense_boost=form_input.dense_boost,
        size=20,
        fuser=form_input.fuser,
        enable_score_normalization=True,
        rrf=False,
        weighting_strategy=weighting_strategy,
    )
    reranker = from_string(form_input.reranker_str)

    st.write("----")

    label_dict: dict[str, str] = query_to_label.get(form_input.query, {})
    if label_dict:
        with st.expander("Labels", expanded=False):
            st.write(label_dict)

    st.write("----")

    st.write("#### Output")
    if not response.results:
        return
    response.results = reranker.rerank(form_input.query, response.results)

    query_vector = query_builder.encode(form_input.query)
    draw_response_stats(response, query_vector, label_dict)

    header = f"{response.total_hits} products found"
    if label_dict:
        retrieved_ids = [result.product["product_id"] for result in response.results]
        judgements = {product_id: label for product_id, (label, product_title) in label_dict.items()}
        relevant_ids = {product_id for product_id, (label, product_title) in label_dict.items() if label == "E"}
        precision = compute_precision(retrieved_ids, relevant_ids)
        recall = compute_recall(retrieved_ids, relevant_ids)
        ndcg = compute_ndcg(retrieved_ids, judgements)
        header = f"{header} (Precision: {precision}, Recall: {recall}, NDCG: {ndcg})"
    st.write(header)
    draw_products(response.results, label_dict)


if __name__ == "__main__":
    main()
