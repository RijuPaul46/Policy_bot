# PolicyBot

PolicyBot is a small Retrieval-Augmented Generation (RAG) API for searching
Wells Fargo policy PDFs. It extracts page-aware text, embeds overlapping chunks
locally, stores vectors in SQLite, and uses Groq for grounded answers when an
API key is configured. A deterministic calculator handles supported EMI
questions without calling an LLM.

## Requirements

- Python 3.10+
- A Groq API key for generated answers (optional for ingestion, retrieval setup,
  health checks, and calculator/greeting routes)
- Network access on first use to download the local embedding model, unless it
  is already cached

## Setup (Windows PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Add your Groq key to .env before asking document questions.
```

Run the API from the project root:

```powershell
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API reference.

## Index policy documents

The bundled `data/documents/financial_policy.pdf` can be indexed with:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/ingest/run
```

Alternatively, upload a PDF through `POST /ingest/upload`. For downloads, set
`POLICY_PDF_URLS` to comma-separated HTTPS PDF URLs hosted on
`wellsfargo.com` or its subdomains, then call `POST /ingest/download`.
Downloading is deliberately restricted to the official domain.

Ingestion writes `data/knowledge_base.json`, `data/chunks.json`,
`data/docs_info.json`, and a persistent SQLite vector index under
`data/vector_db/`. Re-running ingestion replaces the indexed chunks for that
filename.

## Ask questions

```powershell
$body = @{ question = "What does this policy say about account fees?" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/ask `
  -ContentType "application/json" -Body $body
```

Pass the returned `session_id` in later `/ask` requests to preserve a short
conversation context. Sessions are held in memory and are cleared when the
server restarts. Answers cite the source filename and page range; they should
not be treated as financial or legal advice.

## API

- `GET /health` — vector-store status and indexed counts
- `POST /ingest/run` — index local PDFs in `data/documents`
- `POST /ingest/download` — download configured official PDFs and index
- `POST /ingest/upload` — validate and index one uploaded PDF
- `GET /documents` — indexed filenames, page counts, and chunk counts
- `POST /ask` — policy question, calculator request, or greeting
- `GET /sessions/{id}`, `DELETE /sessions/{id}` — inspect/delete in-memory chat

## Tests

```powershell
python -m pytest
```

Tests use deterministic fakes; they do not call Groq or download model weights.

For retrieval evaluation, create a JSON array with a question and its relevant
document filenames, then run:

```powershell
python -m app.evaluation.run_eval .\evaluation_cases.json --top-k 5
```

Each case has the shape
`{"question":"...","expected_filenames":["financial_policy.pdf"]}`.
The runner reports mean reciprocal rank and Hit Rate@3/@5.

## Limitations

- Only text-based PDFs are supported; scanned documents need OCR.
- Relevance threshold and chunk settings should be tuned against a representative
  evaluation set before production use.
- Session history is process-local, and this starter does not include user
  authentication, authorization, rate limiting, or durable chat storage.
- The Groq API is an external service; document content included in prompts is
  sent to the configured provider.
