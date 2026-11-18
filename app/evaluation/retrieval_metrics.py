def hit_rate_at_k(ranked_items: list[str], relevant_items: set[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    return float(any(item in relevant_items for item in ranked_items[:k]))


def reciprocal_rank(ranked_items: list[str], relevant_items: set[str]) -> float:
    for rank, item in enumerate(ranked_items, start=1):
        if item in relevant_items:
            return 1.0 / rank
    return 0.0


def evaluate_retrieval(
    results: list[tuple[list[str], set[str]]],
    ks: tuple[int, ...] = (3, 5),
) -> dict[str, float]:
    if not results:
        raise ValueError("At least one evaluation query is required")
    metrics = {"mrr": sum(reciprocal_rank(r, rel) for r, rel in results) / len(results)}
    for k in ks:
        metrics[f"hit_rate_at_{k}"] = (
            sum(hit_rate_at_k(r, rel, k) for r, rel in results) / len(results)
        )
    return metrics
