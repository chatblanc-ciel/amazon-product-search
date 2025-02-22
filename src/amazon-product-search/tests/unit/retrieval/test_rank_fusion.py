import numpy as np
import pytest

from amazon_product_search.retrieval.rank_fusion import (
    _append_results,
    _borda_counts,
    _combine_responses,
    _min_max_scores,
    _rrf_scores,
)
from amazon_product_search.retrieval.response import Response, Result


def _is_sorted(scores: list[float]) -> None:
    i = 0
    try:
        while i < len(scores) - 1:
            assert scores[i] >= scores[i + 1]
            i += 1
    except AssertionError as err:
        raise AssertionError(f"Given scores are not sorted: {scores}") from err


@pytest.mark.parametrize(
    ("scores", "expected_scores"),
    [
        ([], []),
        ([1], [1]),
        ([2, 1], [1, 0.5]),
        ([2, 1, 0], [1, 0.5, 0]),
    ],
)
def test_min_max_scores(scores, expected_scores):
    results = [Result(product={"product_id": str(i)}, score=score) for i, score in enumerate(scores)]
    response = Response(results=results, total_hits=len(results))
    response = _min_max_scores(response)
    assert [result.score for result in response.results] == expected_scores


@pytest.mark.parametrize(
    ("scores", "expected"),
    [
        ([], []),
        ([1], [1]),
        ([2, 1], [1, 0.5]),
        ([3, 2, 1], [1, 0.5, 0.3333]),
    ],
)
def test_rrf_scores(scores, expected):
    results = [Result(product={"product_id": str(i)}, score=score) for i, score in enumerate(scores)]
    response = Response(results=results, total_hits=len(results))
    response = _rrf_scores(response, k=0)
    actual = [result.score for result in response.results]
    assert np.allclose(actual, expected, atol=1e-04)


@pytest.mark.parametrize(
    ("scores", "expected"),
    [
        ([], []),
        ([1], [1]),
        ([10, 1], [2, 1]),
        ([100, 10, 1], [3, 2, 1]),
    ],
)
def test_borda_counts(scores, expected):
    results = [Result(product={"product_id": str(i)}, score=score) for i, score in enumerate(scores)]
    response = Response(results=results, total_hits=len(results))
    response = _borda_counts(response, n=len(results))
    actual = [result.score for result in response.results]
    assert np.allclose(actual, expected, atol=1e-04)


@pytest.mark.parametrize(
    ("original_results", "alternative_results", "expected_total_hits", "expected_product_ids"),
    [
        ([], [], 0, []),
        (
            [Result(product={"product_id": "1"}, score=0)],
            [],
            1,
            ["1"],
        ),
        (
            [],
            [Result(product={"product_id": "1"}, score=0)],
            1,
            ["1"],
        ),
        (
            [Result(product={"product_id": "1"}, score=0)],
            [Result(product={"product_id": "2"}, score=0)],
            2,
            ["1", "2"],
        ),
        (
            [
                Result(product={"product_id": "1"}, score=0),
                Result(product={"product_id": "2"}, score=0),
            ],
            [Result(product={"product_id": "3"}, score=0)],
            2,
            ["1", "2"],
        ),
        (
            [Result(product={"product_id": "1"}, score=0)],
            [
                Result(product={"product_id": "2"}, score=0),
                Result(product={"product_id": "3"}, score=0),
            ],
            2,
            ["1", "2"],
        ),
    ],
)
def test_append_results(original_results, alternative_results, expected_total_hits, expected_product_ids):
    lexical_response = Response(results=original_results, total_hits=len(original_results))
    semantic_response = Response(results=alternative_results, total_hits=len(alternative_results))
    response = _append_results(lexical_response, semantic_response, size=2)
    assert response.total_hits == expected_total_hits
    assert [result.product["product_id"] for result in response.results] == expected_product_ids


@pytest.mark.parametrize(
    ("lexical_results", "semantic_results", "expected_total_hits", "expected_product_ids"),
    [
        ([], [], 0, []),
        (
            [Result(product={"product_id": "1"}, score=0)],
            [],
            1,
            ["1"],
        ),
        (
            [Result(product={"product_id": "1"}, score=0)],
            [Result(product={"product_id": "1"}, score=0)],
            1,
            ["1"],
        ),
        (
            [Result(product={"product_id": "1"}, score=0), Result(product={"product_id": "2"}, score=0)],
            [],
            2,
            ["2", "1"],
        ),
        (
            [Result(product={"product_id": "1"}, score=0)],
            [Result(product={"product_id": "2"}, score=0)],
            2,
            ["2", "1"],
        ),
        (
            [Result(product={"product_id": "1"}, score=0), Result(product={"product_id": "2"}, score=0)],
            [Result(product={"product_id": "1"}, score=0)],
            2,
            ["2", "1"],
        ),
        (
            [Result(product={"product_id": "1"}, score=0), Result(product={"product_id": "2"}, score=0)],
            [Result(product={"product_id": "3"}, score=0), Result(product={"product_id": "4"}, score=0)],
            4,
            ["4", "3", "2", "1"],
        ),
    ],
)
def test_combine_responses(lexical_results, semantic_results, expected_total_hits, expected_product_ids):
    lexical_response = Response(results=lexical_results, total_hits=len(lexical_results))
    semantic_response = Response(results=semantic_results, total_hits=len(semantic_results))
    response = _combine_responses(lexical_response, semantic_response, combination_method="sum", size=100)
    assert response.total_hits == expected_total_hits
    assert [result.product["product_id"] for result in response.results] == expected_product_ids
    _is_sorted([result.score for result in response.results])


def test_combine_responses_with_size():
    lexical_results = [Result(product={"product_id": str(i)}, score=0) for i in range(0, 3)]
    lexical_response = Response(results=lexical_results, total_hits=len(lexical_results))
    semantic_results = [Result(product={"product_id": str(i)}, score=0) for i in range(3, 6)]
    semantic_response = Response(results=semantic_results, total_hits=len(semantic_results))
    response = _combine_responses(lexical_response, semantic_response, combination_method="sum", size=4)
    assert response.total_hits == 6
    assert len(response.results) == 4
