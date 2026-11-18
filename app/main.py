import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pypdf.errors import PdfReadError

from app.config import get_settings
from app.generation.answerer import Answerer
from app.generation.llm import GroqClient, LLMUnavailableError
from app.generation.query_rewriter import QueryRewriter
from app.ingestion.downloader import download_pdfs
from app.ingestion.pipeline import IngestionPipeline
from app.retrieval.retriever import Retriever
from app.retrieval.vector_store import VectorStore
from app.routing.router import classify_with_llm, route
from app.schemas import (
    AskRequest,
    AskResponse,
    DocumentsResponse,
    HealthResponse,
    IngestResponse,
    SessionResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()
sessions: dict[str, list[dict[str, str]]] = {}


def get_store() -> VectorStore:
    return VectorStore(settings)


def get_pipeline() -> IngestionPipeline:
    return IngestionPipeline(settings, get_store())


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.documents_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled request error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        documents, chunks = get_store().counts()
        persisted = True
        status = "healthy"
    except Exception:
        logger.exception("Unable to query vector store health")
        documents, chunks, persisted, status = 0, 0, False, "degraded"
    return HealthResponse(
        status=status,
        documents_indexed=documents,
        chunks_created=chunks,
        embedding_model=settings.embedding_model,
        llm_model=settings.groq_model,
        vector_store_persisted=persisted,
    )


@app.post("/ingest/run", response_model=IngestResponse)
def ingest_local() -> IngestResponse:
    paths = sorted(settings.documents_dir.glob("*.pdf"))
    try:
        return IngestResponse(**get_pipeline().run(paths))
    except (ValueError, OSError, PdfReadError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/ingest/download", response_model=IngestResponse)
def ingest_downloads() -> IngestResponse:
    if not settings.configured_pdf_urls:
        raise HTTPException(
            status_code=400,
            detail="Configure POLICY_PDF_URLS with comma-separated Wells Fargo PDF URLs.",
        )
    try:
        download_pdfs(settings.configured_pdf_urls, settings.documents_dir)
        return IngestResponse(
            **get_pipeline().run(sorted(settings.documents_dir.glob("*.pdf")))
        )
    except httpx.HTTPError as exc:
        logger.exception("Policy document download failed")
        raise HTTPException(status_code=502, detail="A policy document download failed.") from exc
    except (ValueError, OSError, PdfReadError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/ingest/upload", response_model=IngestResponse)
async def ingest_upload(file: UploadFile = File(...)) -> IngestResponse:
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="PDF exceeds the upload size limit.")
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF.")
    settings.documents_dir.mkdir(parents=True, exist_ok=True)
    destination = settings.documents_dir / filename
    if destination.exists():
        raise HTTPException(status_code=409, detail="A document with this filename already exists.")
    destination.write_bytes(content)
    try:
        return IngestResponse(**get_pipeline().run([destination]))
    except (ValueError, OSError, PdfReadError) as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        destination.unlink(missing_ok=True)
        raise


@app.get("/documents", response_model=DocumentsResponse)
def documents() -> DocumentsResponse:
    try:
        values = get_store().documents()
    except Exception as exc:
        logger.exception("Unable to list indexed documents")
        raise HTTPException(status_code=503, detail="Vector store is unavailable.") from exc
    return DocumentsResponse(
        documents=values,
        total_documents=len(values),
        total_chunks=sum(document["chunks"] for document in values),
    )


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    session_id = request.session_id or str(uuid.uuid4())
    history = sessions.get(session_id, [])
    routed = route(request.question)
    llm = GroqClient(settings)
    if not routed and settings.groq_api_key:
        try:
            routed = classify_with_llm(request.question, llm)
        except Exception:
            logger.exception("Intent classification failed; continuing with retrieval")
    if routed:
        answer, sources, route_name = routed["answer"], [], routed["route"]
    else:
        try:
            query = QueryRewriter(llm).rewrite(request.question, history)
            answer, hits = Answerer(Retriever(settings, get_store()), llm).answer(query)
        except LLMUnavailableError as exc:
            raise HTTPException(
                status_code=503,
                detail="Question answering requires GROQ_API_KEY; retrieval and ingestion remain available.",
            ) from exc
        except Exception as exc:
            logger.exception("Question answering failed")
            raise HTTPException(status_code=502, detail="Question answering failed.") from exc
        sources = [
            {
                "filename": hit["filename"],
                "pages": hit["pages"],
                "score": hit["score"],
                "citation": hit["citation"],
            }
            for hit in hits
        ]
        route_name = "retrieval"

    turns = history + [
        {"role": "user", "content": request.question},
        {"role": "assistant", "content": answer},
    ]
    sessions[session_id] = turns[-settings.max_session_turns * 2 :]
    return AskResponse(
        answer=answer,
        session_id=session_id,
        route=route_name,
        sources=sources,
    )


@app.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str) -> SessionResponse:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    return SessionResponse(session_id=session_id, turns=sessions[session_id])


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str) -> dict[str, str]:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    del sessions[session_id]
    return {"status": "deleted", "session_id": session_id}