from typing import Any, Optional

import streamlit as st

from amazon_product_search.es import query_builder
from amazon_product_search.es.es_client import EsClient
from amazon_product_search.es.response import Result
from amazon_product_search.nlp.encoder import Encoder
from amazon_product_search.nlp.normalizer import normalize_query
from demo.page_config import set_page_config

es_client = EsClient()
encoder = Encoder()


def draw_es_query(query: Optional[dict[str, Any]], knn_query: Optional[dict[str, Any]], size: int):
    es_query: dict[str, Any] = {
        "size": size,
    }

    if query:
        es_query["query"] = query

    if knn_query:
        es_query["knn"] = knn_query

    st.write("Elasticsearch Query:")
    st.write(es_query)


def draw_products(results: list[Result]):
    for result in results:
        with st.expander(f"{result.product['product_title']} ({result.score})"):
            st.write(result.product)
            st.write(result.explanation)


def main():
    set_page_config()

    size = 20

    st.write("## Search")

    st.write("#### Input")
    indices = es_client.list_indices()
    index_name = st.selectbox("Index:", indices)

    query = st.text_input("Query:")
    normalized_query = normalize_query(query)

    columns = st.columns(2)
    is_sparse_enabled = columns[0].checkbox("Sparse:", value=True)
    is_dense_enabled = columns[1].checkbox("Dense:", value=False)

    fields = ["product_title"]
    if st.checkbox("Use description"):
        fields.append("product_description")
    if st.checkbox("Use bullet point"):
        fields.append("product_bullet_point")
    if st.checkbox("Use brand"):
        fields.append("product_brand")
    if st.checkbox("Use color name"):
        fields.append("product_color_name")

    es_query = None
    if is_sparse_enabled:
        es_query = query_builder.build_multimatch_search_query(
            query=normalized_query,
            fields=fields,
        )
    es_knn_query = None
    if normalized_query and is_dense_enabled:
        query_vector = encoder.encode(normalized_query, show_progress_bar=False)
        es_knn_query = query_builder.build_knn_search_query(query_vector, field="product_vector", top_k=size)

    st.write("----")

    with st.expander("Query Details", expanded=False):
        st.write("Normalized Query:")
        st.write(normalized_query)

        st.write("Analyzed Query")
        analyzed_query = es_client.analyze(query)
        st.write(analyzed_query)

        draw_es_query(es_query, es_knn_query, size)

    st.write("----")

    st.write("#### Output")
    response = es_client.search(index_name=index_name, query=es_query, knn_query=es_knn_query, size=size, explain=True)
    st.write(f"{response.total_hits} products found")
    draw_products(response.results)


if __name__ == "__main__":
    main()
