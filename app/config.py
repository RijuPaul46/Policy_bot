from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "PolicyBot"
    data_dir: Path = Path("data")
    documents_dir: Path = Path("data/documents")
    vector_db_dir: Path = Path("data/vector_db")
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_top_k: int = 5
    retrieval_distance_threshold: float = 0.72
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_timeout_seconds: float = 45.0
    policy_pdf_urls: str = ""
    max_upload_bytes: int = 20 * 1024 * 1024
    max_session_turns: int = 4

    @property
    def configured_pdf_urls(self) -> list[str]:
        return [url.strip() for url in self.policy_pdf_urls.split(",") if url.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()