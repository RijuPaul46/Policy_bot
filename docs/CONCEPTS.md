# RAG concepts in PolicyBot

1. **Extraction:** `app/ingestion/extractor.py` reads PDF pages and records
   half-open character offsets. Page offsets keep citations tied to the source.
2. **Chunking:** `app/ingestion/chunker.py` splits extracted text with overlap.
   Overlap helps keep a fact and its nearby explanation in the same retrieval
   neighborhood.
3. **Embeddings:** `app/retrieval/embeddings.py` converts text to normalized
   vectors using a local SentenceTransformer model.
4. **Vector storage:** SQLite persists vectors, text, and source metadata so an
   application restart does not require re-indexing.
5. **Similarity:** The local store computes cosine similarity against the
   normalized vectors. PolicyBot converts it to a distance and applies a cutoff.
6. **Grounding:** Retrieved passages are the only factual context provided to
   the answer prompt. Missing evidence leads to a refusal rather than a guess.
7. **Citations:** Each retrieved passage receives a source label containing its
   filename and page range; the prompt asks the model to cite those labels.
8. **Prompt injection:** Policy text is untrusted input. The system prompt
   directs the model to use it as evidence, not as instructions.
9. **Conversation rewriting:** Follow-up questions can be rewritten as a
   standalone search query using a bounded in-memory conversation history.
10. **Tool routing:** Greetings and a narrow EMI pattern avoid an LLM call.
    EMI calculations use `Decimal`, not dynamic code evaluation.
11. **Resilience:** Groq transport errors use bounded exponential retries.
    Missing credentials and service failures return explicit HTTP errors.
12. **Evaluation:** Run focused unit tests first; a real RAG evaluation should
    separately measure retrieval relevance and answer faithfulness.
13. **Production readiness:** This project is an educational starter. Add
    authentication, authorization, durable sessions, observability, and a
    representative quality benchmark before deployment.
