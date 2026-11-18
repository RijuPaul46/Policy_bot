import pytest

from app.evaluation.retrieval_metrics import (
    evaluate_retrieval,
    hit_rate_at_k,
    reciprocal_rank,
)


def test_retrieval_metrics_use_ranked_document_hits():
    ranked = ["unrelated.pdf", "policy.pdf"]
    relevant = {"policy.pdf"}

    assert hit_rate_at_k(ranked, relevant, 1) == 0
    assert hit_rate_at_k(ranked, relevant, 2) == 1
    assert reciprocal_rank(ranked, relevant) == 0.5


def test_evaluate_retrieval_rejects_empty_cases():
    with pytest.raises(ValueError):
        evaluate_retrieval([])
