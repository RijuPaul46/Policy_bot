from fastapi.testclient import TestClient

import app.main as main


class EmptyStore:
    def counts(self):
        return 0, 0

    def documents(self):
        return []

    def search(self, query, top_k):
        return []


class RelevantStore(EmptyStore):
    def search(self, query, top_k):
        return [
            {
                "text": "The policy excerpt.",
                "filename": "policy.pdf",
                "pages": [2],
                "score": 0.9,
                "distance": 0.1,
            }
        ]

def test_health_and_documents_endpoints(monkeypatch):
    monkeypatch.setattr(main, "get_store", lambda: EmptyStore())

    with TestClient(main.app) as client:
        health = client.get("/health")
        documents = client.get("/documents")

    assert health.status_code == 200
    assert health.json()["status"] == "healthy"
    assert documents.json() == {
        "documents": [],
        "total_documents": 0,
        "total_chunks": 0,
    }


def test_greeting_and_session_lifecycle():
    main.sessions.clear()
    with TestClient(main.app) as client:
        result = client.post("/ask", json={"question": "Hello"})
        session_id = result.json()["session_id"]
        session = client.get(f"/sessions/{session_id}")
        deleted = client.delete(f"/sessions/{session_id}")

    assert result.status_code == 200
    assert result.json()["route"] == "out_of_scope"
    assert len(session.json()["turns"]) == 2
    assert deleted.status_code == 200


def test_ask_without_evidence_abstains_without_llm(monkeypatch):
    monkeypatch.setattr(main.settings, "groq_api_key", None)
    monkeypatch.setattr(main, "get_store", lambda: EmptyStore())

    with TestClient(main.app) as client:
        response = client.post("/ask", json={"question": "What is the policy?"})

    assert response.status_code == 200
    assert response.json()["answer"].startswith("I could not find")


def test_ask_requires_groq_key_when_relevant_context_exists(monkeypatch):
    monkeypatch.setattr(main.settings, "groq_api_key", None)
    monkeypatch.setattr(main, "get_store", lambda: RelevantStore())

    with TestClient(main.app) as client:
        response = client.post("/ask", json={"question": "What is the policy?"})

    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"]
