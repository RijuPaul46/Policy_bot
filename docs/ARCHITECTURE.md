# Architecture

## Ingestion

```mermaid
flowchart LR
    PDF[PDF file] --> Extract[Extract page text and offsets]
    Extract --> Split[Overlapping page-aware chunks]
    Split --> Embed[Local SentenceTransformer]
    Embed --> SQLite[Persistent SQLite vector index]
    Split --> JSON[Inspectable JSON exports]
```

## Question answering

```mermaid
flowchart LR
    User --> API[FastAPI /ask]
    API --> Route{Fast rule}
    Route -->|Greeting or EMI| Tool[Deterministic response]
    Route -->|Policy question| Rewrite[Optional history rewrite]
    Rewrite --> Search[Cosine vector retrieval]
    Search --> Context[Threshold + source labels]
    Context --> Groq[Grounded Groq completion]
    Groq --> API
    Tool --> API
```

The vector store uses cosine distance (`0` is closest); the retriever rejects
results above the configured distance threshold. Citations are built from the
chunk's source filename and overlapping PDF page metadata.
