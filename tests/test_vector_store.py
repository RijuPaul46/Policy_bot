from app.config import Settings
from app.retrieval import vector_store
from app.retrieval.vector_store import VectorStore


def test_persistent_store_search_and_replace(monkeypatch, tmp_path):
    def fake_embeddings(texts):
        return [
            [1.0, 0.0] if text in {"policy chunk", "query"} else [0.0, 1.0]
            for text in texts
        ]

    monkeypatch.setattr(vector_store, "embed_texts", fake_embeddings)
    store = VectorStore(Settings(vector_db_dir=tmp_path / "vectors"))
    store.upsert(
        [
            {
                "id": "policy-1",
                "filename": "policy.pdf",
                "text": "policy chunk",
                "pages": [2],
                "start": 0,
                "end": 10,
                "document_hash": "old",
            },
            {
                "id": "other-1",
                "filename": "other.pdf",
                "text": "unrelated",
                "pages": [1],
                "start": 0,
                "end": 9,
                "document_hash": "other",
            },
        ]
    )

    assert store.search("query", 2)[0]["filename"] == "policy.pdf"
    store.upsert(
        [
            {
                "id": "policy-2",
                "filename": "policy.pdf",
                "text": "replacement chunk",
                "pages": [3],
                "start": 0,
                "end": 15,
                "document_hash": "new",
            }
        ]
    )

    assert store.counts() == (2, 2)
    assert {item["filename"] for item in store.documents()} == {
        "policy.pdf",
        "other.pdf",
    }
