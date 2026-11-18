from collections.abc import Iterator
from contextlib import contextmanager
import sqlite3
from threading import Lock

import numpy as np

from app.config import Settings
from app.retrieval.embeddings import embed_texts


class VectorStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.settings.vector_db_dir.mkdir(parents=True, exist_ok=True)
        self.database_path = self.settings.vector_db_dir / "policybot.sqlite3"
        self._lock = Lock()
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    text TEXT NOT NULL,
                    pages TEXT NOT NULL,
                    start_offset INTEGER NOT NULL,
                    end_offset INTEGER NOT NULL,
                    document_hash TEXT NOT NULL,
                    embedding BLOB NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS chunks_filename_idx ON chunks(filename)"
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def upsert(self, chunks: list[dict]) -> None:
        if not chunks:
            return
        embeddings = embed_texts([chunk["text"] for chunk in chunks])
        filenames = sorted({chunk["filename"] for chunk in chunks})
        placeholders = ",".join("?" for _ in filenames)
        rows = [
            (
                chunk["id"],
                chunk["filename"],
                chunk["text"],
                ",".join(str(page) for page in chunk["pages"]),
                chunk["start"],
                chunk["end"],
                chunk["document_hash"],
                np.asarray(vector, dtype=np.float32).tobytes(),
            )
            for chunk, vector in zip(chunks, embeddings, strict=True)
        ]
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                f"DELETE FROM chunks WHERE filename IN ({placeholders})",
                filenames,
            )
            connection.executemany(
                """
                INSERT INTO chunks
                    (id, filename, text, pages, start_offset, end_offset,
                     document_hash, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def search(self, query: str, top_k: int) -> list[dict]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT text, filename, pages, embedding FROM chunks"
            ).fetchall()
        if not rows:
            return []
        query_vector = np.asarray(embed_texts([query])[0], dtype=np.float32)
        ranked: list[dict] = []
        for row in rows:
            stored_vector = np.frombuffer(row["embedding"], dtype=np.float32)
            score = float(np.dot(query_vector, stored_vector))
            score = max(0.0, min(1.0, score))
            ranked.append(
                {
                    "text": row["text"],
                    "filename": row["filename"],
                    "pages": [
                        int(page) for page in row["pages"].split(",") if page
                    ],
                    "score": score,
                    "distance": 1.0 - score,
                }
            )
        ranked.sort(key=lambda hit: hit["score"], reverse=True)
        return ranked[:top_k]

    def counts(self) -> tuple[int, int]:
        with self._connect() as connection:
            documents, chunks = connection.execute(
                "SELECT COUNT(DISTINCT filename), COUNT(*) FROM chunks"
            ).fetchone()
        return documents, chunks

    def documents(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT filename, pages FROM chunks").fetchall()
        counts: dict[str, dict[str, int]] = {}
        for row in rows:
            entry = counts.setdefault(row["filename"], {"pages": 0, "chunks": 0})
            entry["chunks"] += 1
            pages = [int(page) for page in row["pages"].split(",") if page]
            entry["pages"] = max(entry["pages"], max(pages, default=0))
        return [
            {"filename": filename, **details}
            for filename, details in sorted(counts.items())
        ]
