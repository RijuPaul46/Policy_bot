from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, max_length=100)


class SourceCitation(BaseModel):
    filename: str
    pages: list[int]
    score: float
    citation: str


class AskResponse(BaseModel):
    answer: str
    session_id: str
    route: Literal["retrieval", "calculator", "out_of_scope"]
    sources: list[SourceCitation] = Field(default_factory=list)


class IngestResponse(BaseModel):
    documents_indexed: int
    chunks_created: int
    filenames: list[str]


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    documents_indexed: int
    chunks_created: int
    embedding_model: str
    llm_model: str
    vector_store_persisted: bool


class DocumentInfo(BaseModel):
    filename: str
    pages: int
    chunks: int


class DocumentsResponse(BaseModel):
    documents: list[DocumentInfo]
    total_documents: int
    total_chunks: int


class SessionResponse(BaseModel):
    session_id: str
    turns: list[dict[str, str]]
