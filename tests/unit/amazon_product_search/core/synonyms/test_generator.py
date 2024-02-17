import polars as pl
import pytest

from amazon_product_search.core.synonyms.generator import (
    generate_ngrams,
    generate_ngrams_all,
    preprocess_query_title_pairs,
)


def test_preprocess_query_title_pairs():
    df = pl.from_dicts(
        [
            {"query": "Hello", "product_title": "World"},
            {"query": None, "product_title": "product_title"},
            {"query": "query", "product_title": None},
        ]
    )
    df = preprocess_query_title_pairs(df)
    assert df.to_dicts() == [{"query": "hello", "product_title": "world"}]


@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (1, ["ab", "cd", "ef", "gh"]),
        (2, ["ab cd", "cd ef", "ef gh"]),
        (3, ["ab cd ef", "cd ef gh"]),
        (4, ["ab cd ef gh"]),
        (5, []),
    ],
)
def test_generate_ngrams(n, expected):
    tokens = ["ab", "cd", "ef", "gh"]
    ngrams = generate_ngrams(tokens, n)
    assert ngrams == expected


def test_generate_ngrams_all():
    tokens = ["ab", "cd", "ef", "gh"]
    ngrams = generate_ngrams_all(tokens, 3)
    assert ngrams == ["ab", "cd", "ef", "gh", "ab cd", "cd ef", "ef gh", "ab cd ef", "cd ef gh"]
