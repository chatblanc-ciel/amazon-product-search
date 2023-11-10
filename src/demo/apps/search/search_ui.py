from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from amazon_product_search.core.es.response import Response, Result
from amazon_product_search.core.metrics import compute_cosine_similarity


@dataclass
class FormInput:
    query: str | None
    fields: list[str]
    sparse_boost: float
    dense_boost: float
    query_type: str | None
    is_synonym_expansion_enabled: bool
    size: int
    window_size: int
    fuser: str
    fusion_strategy: str
    normalization_strategy: Literal["min_max", "rrf"] | None
    weighting_strategy: str
    reranker_str: str | None


def draw_input_form(queries: list[str] | None = None) -> FormInput:
    query = st.selectbox("Query:", queries) if queries else st.text_input("Query:")

    fields = st.multiselect(
        "Fields:",
        options=[
            "product_title",
            "product_description",
            "product_bullet_point",
            "product_brand",
            "product_color",
            "product_vector",
        ],
        default=["product_title"],
    )

    columns = st.columns(2)
    with columns[0]:
        sparse_boost = st.number_input("Sparse Boost", value=1.0)
    with columns[1]:
        dense_boost = st.number_input("Dense Boost", value=1.0)

    query_type = st.selectbox(
        "Query Type:",
        options=[
            "combined_fields",
            "cross_fields",
            "best_fields",
            "simple_query_string",
        ],
    )

    is_synonym_expansion_enabled = st.checkbox("enable_synonym_expansion")

    size = st.number_input("size", value=100)

    window_size = st.number_input("window_size", value=100)

    fuser = st.selectbox("fuser:", ["own", "search_engine"])

    fusion_strategy = st.selectbox("fusion_strategy:", ["fuse", "append"])

    normalization_strategy = st.selectbox("normalization_strategy:", ["min_max", "rrf"])

    weighting_strategy = st.selectbox("weighting_strategy:", ["fixed", "dynamic"])

    reranker_str = st.selectbox("reranker:", ["NoOpReranker", "RandomReranker", "DotReranker"])

    return FormInput(
        query,
        fields,
        sparse_boost,
        dense_boost,
        query_type,
        is_synonym_expansion_enabled,
        size=size,
        window_size=window_size,
        fuser=fuser,
        fusion_strategy=fusion_strategy,
        normalization_strategy=normalization_strategy,
        weighting_strategy=weighting_strategy,
        reranker_str=reranker_str,
    )


def draw_response_stats(response: Response, query_vector: np.ndarray, label_dict: dict[str, tuple[str, str]]) -> None:
    rows = []
    for result in response.results:
        sparse_score, dense_score = result.get_scores_in_explanation()
        row = {
            "product_title": result.product["product_title"],
            "total_score": result.score,
            "sparse_score": sparse_score,
            "dense_score": dense_score,
            "label": label_dict.get(result.product["product_id"], ("-", ""))[0],
        }
        rows.append(row)
    df = pd.DataFrame(rows)

    with st.expander("Response Stats"):
        st.write(df)

        rows = []
        for i, row in enumerate(df.to_dict(orient="records")):
            rows.append(
                {
                    "retrieval": "sparse",
                    "rank": i,
                    "score": row["sparse_score"],
                }
            )
            rows.append(
                {
                    "retrieval": "dense",
                    "rank": i,
                    "score": row["dense_score"],
                }
            )
        scores_df = pd.DataFrame(rows)
        fig = px.bar(scores_df, x="rank", y="score", color="retrieval")
        fig.update_layout(title="Scores by Rank")
        st.plotly_chart(fig, use_container_width=True)

        cols = st.columns(2)
        with cols[0]:
            fig = px.histogram(scores_df, x="score", color="retrieval", barmode="overlay")
            fig.update_layout(title="Histogram of Scores by Retrieval")
            st.plotly_chart(fig, use_container_width=True)
        with cols[1]:
            df["label"] = df["label"].astype("category")
            fig = px.scatter(df, x="sparse_score", y="dense_score", color="label")
            fig.update_layout(title="Scores and Labels")
            st.plotly_chart(fig, use_container_width=True)

        if not response.results:
            return
        if not response.results[0].product.get("product_vector"):
            return
        product_vectors = np.array([result.product["product_vector"] for result in response.results])
        scores = compute_cosine_similarity(query_vector, product_vectors)
        scores_df = pd.DataFrame([{"i": i, "score": score} for i, score in enumerate(scores)])
        fig = px.line(scores_df, x="i", y="score")
        fig.update_layout(title="Cosine Similarity")
        st.plotly_chart(fig, use_container_width=True)


def draw_products(results: list[Result], label_dict: dict[str, tuple[str, str]]) -> None:
    for result in results:
        product = result.product
        header = f"{result.product['product_title']} ({result.score})"
        if label_dict:
            label = {
                "E": "[Exact] ",
                "S": "[Substitute] ",
                "C": "[Complement] ",
                "I": "[Irrelevant] ",
                "-": "",
            }[label_dict.get(product["product_id"], ("-", ""))[0]]
            header = f"{label}{header}"
        with st.expander(header):
            st.write(result.product)
            if result.explanation:
                st.write(result.explanation)
