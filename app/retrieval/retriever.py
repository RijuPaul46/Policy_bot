from app.config import Settings
from app.retrieval.vector_store import VectorStore


class Retriever:
    def __init__(self, settings: Settings, store: VectorStore):
        self.settings = settings
        self.store = store

    def retrieve(self, query: str) -> list[dict]:
        return [
            hit
            for hit in self.store.search(query, self.settings.retrieval_top_k)
            if hit["distance"] <= self.settings.retrieval_distance_threshold
        ]

    @staticmethod
    def citation(hit: dict, index: int) -> str:
        pages = hit["pages"]
        page_label = (
            str(pages[0])
            if len(pages) == 1
            else f"{pages[0]}-{pages[-1]}"
            if pages
            else "unknown"
        )
        return f"[Source {index} | {hit['filename']} | pages {page_label}]"
