from typing import Optional

import numpy as np

LABEL_TO_REL: dict[str, float] = {
    "E": 1.0,
    "S": 0.1,
    "C": 0.01,
    "I": 0.0,
}


def compute_zero_hit_rate(xs: list[int]) -> Optional[float]:
    if len(xs) == 0:
        return None
    return round(len([x for x in xs if x == 0]) / len(xs), 4)


def compute_recall(retrieved_ids: list[str], relevant_ids: set[str], k: Optional[int] = None) -> Optional[float]:
    if not relevant_ids:
        return None
    if k:
        retrieved_ids = retrieved_ids[:k]
    return round(len(set(retrieved_ids) & relevant_ids) / len(relevant_ids), 4)


def compute_precision(
    retrieved_ids: list[str], relevant_ids: set[str], k: Optional[int] = None, zero_hits_to_none: bool = True
) -> Optional[float]:
    if not retrieved_ids:
        return None if zero_hits_to_none else 0.0
    if k:
        retrieved_ids = retrieved_ids[:k]
    return round(len((set(retrieved_ids) & relevant_ids)) / len(retrieved_ids), 4)


def compute_iou(a: set[str], b: set[str]) -> tuple[Optional[float], set[str], set[str]]:
    union = a | b
    intersection = a & b
    iou = round(len(intersection) / len(union), 4) if union else None
    return iou, intersection, union


def compute_ap(retrieved_ids: list[str], relevant_ids: set[str]) -> Optional[float]:
    if not retrieved_ids or not relevant_ids:
        return None

    gain = 0.0
    num_relevant_docs = 0
    for i, retrieved_id in enumerate(retrieved_ids):
        if retrieved_id in relevant_ids:
            num_relevant_docs += 1
            gain += num_relevant_docs / (i + 1)
    if num_relevant_docs == 0:
        return None
    return round(gain / num_relevant_docs, 4)


def compute_rr(retrieved_ids: list[str], relevant_ids: set[str], k: Optional[int] = None) -> Optional[float]:
    if not relevant_ids:
        return None
    if k:
        retrieved_ids = retrieved_ids[:k]
    for i, retrieved_id in enumerate(retrieved_ids):
        if retrieved_id in relevant_ids:
            return round(1 / (i + 1), 4)
    return 0.0


def compute_dcg(rels: list[float]) -> float:
    result = 0.0
    for i, rel in enumerate(rels):
        result += (2**rel - 1) / np.log2(i + 2)
    return result


def compute_ndcg(
    retrieved_ids: list[str],
    id_to_label: dict[str, str],
    prime: bool = False,
    k: Optional[int] = None,
) -> Optional[float]:
    """Compute Normalized Discounted Cumulative Gain (NDCG) based on the given relevance judgements.

    NDCG' is a variant of NDCG that calculates the score using only annotated documents.

    Args:
        retrieved_ids (list[str]): Document IDs retrieved from a search engine.
        id_to_label (dict[str, str]): A dict composed of document IDs and their relevance judgements (ESCI).
        prime (bool, optional): True to skip unseen documents. Defaults to False.

    Returns:
        Optional[float]: The computed score or None.
    """
    if k:
        retrieved_ids = retrieved_ids[:k]
    if prime:
        y_pred = [LABEL_TO_REL[id_to_label[doc_id]] for doc_id in retrieved_ids if doc_id in id_to_label]
    else:
        y_pred = [LABEL_TO_REL[id_to_label[doc_id]] if doc_id in id_to_label else 0 for doc_id in retrieved_ids]
    y_true = sorted(y_pred, reverse=True)
    idcg_val = compute_dcg(y_true)
    dcg_val = compute_dcg(y_pred)

    if idcg_val > 0:
        # If IDCG > 0, it means that the search results contain relevant documents.
        # In this case, calculate NDCG as usual.
        return round(dcg_val / idcg_val, 4)
    elif any(label for label in id_to_label.values() if label != "I"):
        # If IDCG == 0 and the products labeled as E, S, or C exist in the dataset,
        # it means that the search results do not contain any relevant documents.
        # In this case, NDCG is 0.
        return 0.0
    return None


def compute_cosine_similarity(query_vector: np.ndarray, product_vectors: np.ndarray) -> np.ndarray:
    numerator = np.dot(query_vector, product_vectors.T)
    denominator = np.linalg.norm(query_vector) * np.linalg.norm(product_vectors, axis=1)
    return numerator / denominator


def compute_alteration_count(mixed_list: list[str | None]) -> int:
    if not mixed_list:
        return 0

    alternation_count = 0
    current_source = mixed_list[0]

    for element in mixed_list[1:]:
        if element is None:
            continue
        if element == current_source:
            continue
        if current_source is not None:
            alternation_count += 1
        current_source = element

    return alternation_count
