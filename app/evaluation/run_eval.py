import argparse
import json
from pathlib import Path

from app.config import get_settings
from app.evaluation.retrieval_metrics import evaluate_retrieval
from app.retrieval.retriever import Retriever
from app.retrieval.vector_store import VectorStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate PolicyBot retrieval quality.")
    parser.add_argument(
        "cases",
        type=Path,
        help='JSON array of {"question": "...", "expected_filenames": ["..."]} cases',
    )
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be positive")
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        parser.error("cases file must contain a non-empty JSON array")

    settings = get_settings()
    settings.retrieval_top_k = args.top_k
    retriever = Retriever(settings, VectorStore(settings))
    results = []
    for case in cases:
        hits = retriever.retrieve(case["question"])
        ranked = [hit["filename"] for hit in hits]
        relevant = set(case["expected_filenames"])
        results.append((ranked, relevant))
    print(json.dumps(evaluate_retrieval(results), indent=2))


if __name__ == "__main__":
    main()
