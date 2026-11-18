import json
import logging
import re
from pathlib import Path

from app.config import Settings
from app.ingestion.chunker import split_text
from app.ingestion.extractor import extract_pdf
from app.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)


def _safe_id(filename: str, document_hash: str, start: int) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", Path(filename).stem).strip("-") or "document"
    return f"{slug}-{document_hash[:12]}-{start}"


class IngestionPipeline:
    def __init__(self, settings: Settings, store: VectorStore):
        self.settings = settings
        self.store = store

    def run(self, paths: list[Path]) -> dict:
        if not paths:
            raise ValueError(f"No PDF files found in {self.settings.documents_dir}")
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        all_chunks: list[dict] = []
        documents: list[dict] = []

        for path in paths:
            extracted = extract_pdf(path)
            chunks = split_text(
                extracted["text"],
                extracted["page_info"],
                self.settings.chunk_size,
                self.settings.chunk_overlap,
            )
            for chunk in chunks:
                chunk["id"] = _safe_id(path.name, extracted["sha256"], chunk["start"])
                chunk["filename"] = path.name
                chunk["document_hash"] = extracted["sha256"]
            documents.append(
                {
                    "filename": path.name,
                    "pages": extracted["page_count"],
                    "sha256": extracted["sha256"],
                    "chunks": len(chunks),
                }
            )
            all_chunks.extend(chunks)

        self.store.upsert(all_chunks)
        (self.settings.data_dir / "knowledge_base.json").write_text(
            json.dumps(documents, indent=2), encoding="utf-8"
        )
        (self.settings.data_dir / "chunks.json").write_text(
            json.dumps(all_chunks, indent=2), encoding="utf-8"
        )
        (self.settings.data_dir / "docs_info.json").write_text(
            json.dumps(documents, indent=2), encoding="utf-8"
        )
        logger.info("Indexed %d PDFs into %d chunks", len(documents), len(all_chunks))
        return {
            "documents_indexed": len(documents),
            "chunks_created": len(all_chunks),
            "filenames": [document["filename"] for document in documents],
        }
