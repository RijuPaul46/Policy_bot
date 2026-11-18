from threading import Lock

from sentence_transformers import SentenceTransformer

from app.config import get_settings

_model: SentenceTransformer | None = None
_lock = Lock()


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                _model = SentenceTransformer(get_settings().embedding_model, device="cpu")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    vectors = get_embedding_model().encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vectors.tolist()
