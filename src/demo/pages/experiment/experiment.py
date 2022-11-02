from dataclasses import asdict, dataclass
from typing import Any, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from amazon_product_search import source
from amazon_product_search.es import query_builder
from amazon_product_search.es.es_client import EsClient
from amazon_product_search.es.response import Response
from amazon_product_search.metrics import compute_ap, compute_ndcg, compute_recall, compute_zero_hit_rate
from amazon_product_search.nlp.encoder import Encoder
from amazon_product_search.nlp.normalizer import normalize_query
from demo.page_config import set_page_config

es_client = EsClient()
encoder = Encoder()


@dataclass
class SearchConfig:
    name: str
    is_sparse_enabled: bool = True
    is_dense_enabled: bool = False
    use_description: bool = False
    use_bullet_point: bool = False
    use_brand: bool = False
    use_color_name: bool = False
    top_k: int = 100


Variant = SearchConfig


@dataclass
class ExperimentalSetup:
    locale: str
    variants: list[Variant]
    num_queries: Optional[int] = None

    @property
    def index_name(self) -> str:
        return f"products_{self.locale}"


@st.cache
def load_labels(experimental_setup: ExperimentalSetup) -> pd.DataFrame:
    df = source.load_labels(experimental_setup.locale)
    if experimental_setup.num_queries:
        queries = df["query"].unique()[: experimental_setup.num_queries]
        df = df[df["query"].isin(queries)]
    return df


def count_docs(index_name: str) -> int:
    return es_client.count_docs(index_name)


def draw_variants(variants: list[Variant]):
    variants_df = pd.DataFrame([asdict(variant) for variant in variants])
    st.write(variants_df)


def search(index_name: str, query: str, config: SearchConfig) -> Response:
    es_query = None
    es_knn_query = None

    if config.is_sparse_enabled:
        es_query = query_builder.build_multimatch_search_query(
            query=query,
            use_description=config.use_description,
            use_bullet_point=config.use_bullet_point,
            use_brand=config.use_brand,
            use_color_name=config.use_color_name,
        )
    if config.is_dense_enabled:
        query_vector = encoder.encode(query, show_progress_bar=False)
        es_knn_query = query_builder.build_knn_search_query(query_vector, top_k=config.top_k)

    return es_client.search(index_name=index_name, query=es_query, knn_query=es_knn_query, size=config.top_k)


def compute_metrics(index_name: str, query: str, variant: Variant, labels_df: pd.DataFrame) -> dict[str, Any]:
    response = search(index_name, query, variant)

    retrieved_ids = [result.product["product_id"] for result in response.results]
    relevant_ids = set(labels_df[labels_df["esci_label"] == "exact"]["product_id"].tolist())
    judgements: dict[str, str] = {row["product_id"]: row["esci_label"] for row in labels_df.to_dict("records")}
    return {
        "variant": variant.name,
        "query": query,
        "total_hits": response.total_hits,
        "recall": compute_recall(retrieved_ids, relevant_ids),
        "ap": compute_ap(retrieved_ids, relevant_ids),
        "ndcg": compute_ndcg(retrieved_ids, judgements),
    }


def perform_search(experimental_setup: ExperimentalSetup, query_dict: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    total_examples = len(query_dict)
    n = 0
    progress_text = st.empty()
    progress_bar = st.progress(0)
    metrics = []
    for query, query_labels_df in query_dict.items():
        n += 1
        query = normalize_query(query)
        progress_text.text(f"Query ({n} / {total_examples}): {query}")
        progress_bar.progress(n / total_examples)
        for variant in experimental_setup.variants:
            metrics.append(compute_metrics(experimental_setup.index_name, query, variant, query_labels_df))
    progress_text.text(f"Done ({n} / {total_examples})")
    return metrics


def compute_stats(metrics_df: pd.DataFrame) -> pd.DataFrame:
    stats_df = (
        metrics_df.groupby("variant")
        .agg(
            total_hits=("total_hits", lambda series: round(np.mean(series))),
            zero_hit_rate=("total_hits", lambda series: compute_zero_hit_rate(series.values)),
            recall=("recall", "mean"),
            map=("ap", "mean"),
            ndcg=("ndcg", "mean"),
        )
        .reset_index()
    )
    return stats_df


def draw_figures(metrics_df: pd.DataFrame):
    for metric in ["total_hits", "recall", "ap", "ndcg"]:
        fig = px.box(metrics_df, y=metric, color="variant")
        st.plotly_chart(fig)


def main():
    set_page_config()

    st.write("## Experiments")

    st.write("### Experimental Setup")
    experimental_setup = ExperimentalSetup(
        locale="jp",
        num_queries=100,
        variants=[
            SearchConfig(name="sparse", is_sparse_enabled=True, is_dense_enabled=False, top_k=100),
            SearchConfig(name="dense", is_sparse_enabled=False, is_dense_enabled=True, top_k=100),
            SearchConfig(name="hybrid", is_sparse_enabled=True, is_dense_enabled=True, top_k=100),
        ],
    )
    num_docs = count_docs(experimental_setup.index_name)

    labels_df = load_labels(experimental_setup)
    query_dict: dict[str, pd.DataFrame] = {}
    for query, query_labels_df in labels_df.groupby("query"):
        query_dict[query] = query_labels_df

    content = f"""
    The experiment is conducted on `{experimental_setup.index_name}` containing {num_docs} docs in total.
    We send {len(query_dict)} queries to the index with different parameters shown below.
    Then, we compute Total Hits, Zero Hit Rate, Recall, MAP, and NDCG on each variant.
    """
    st.write(content)

    st.write("#### Variants")
    draw_variants(experimental_setup.variants)

    clicked = st.button("Run")

    if not clicked:
        return

    metrics = perform_search(experimental_setup, query_dict)

    st.write("----")

    st.write("### Experimental Results")
    metrics_df = pd.DataFrame(metrics)

    st.write("#### Metrics by query")
    with st.expander("click to expand"):
        st.write(metrics_df)

    st.write("#### Metrics by variant")
    stats_df = compute_stats(metrics_df)
    st.write(stats_df)

    st.write("#### Analysis")
    draw_figures(metrics_df)


if __name__ == "__main__":
    main()