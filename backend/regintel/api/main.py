"""FastAPI application for the Regulatory Intelligence Platform."""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..config import get_settings
from . import queries, rag
from .routes_phase2 import router as phase2_router

app = FastAPI(
    title="Regulatory Intelligence Platform",
    description="AI-driven interpretation, search, and risk visualization over a "
                "global medical-device regulatory corpus.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(phase2_router)


@app.get("/api/health")
def health():
    s = get_settings()
    return {"status": "ok", "claude_enabled": s.claude_enabled, "model": s.model}


# ----------------------------- corpus sync -----------------------------

@app.get("/api/ingest/status")
def ingest_status():
    from .. import ingest_service

    s = get_settings()
    return {**ingest_service.last_status(), "autoingest_minutes": s.autoingest_minutes}


@app.post("/api/ingest/run")
async def ingest_run(interpret: bool = False):
    """On-demand corpus sync (the Sync button). Runs off the event loop."""
    import asyncio

    from .. import ingest_service

    return await asyncio.to_thread(ingest_service.run_sync, interpret)


@app.on_event("startup")
async def _start_scheduler():
    import asyncio

    from .. import ingest_service

    s = get_settings()
    if s.autoingest_minutes <= 0:
        return

    async def _loop():
        while True:
            await asyncio.sleep(s.autoingest_minutes * 60)
            try:
                await asyncio.to_thread(ingest_service.run_sync, s.autoingest_interpret)
            except Exception as exc:  # keep the scheduler alive on errors
                print(f"[auto-ingest] error: {exc}")

    asyncio.create_task(_loop())
    print(f"[auto-ingest] scheduled every {s.autoingest_minutes} min")


@app.get("/api/stats")
def stats():
    return queries.corpus_stats()


@app.get("/api/facets")
def get_facets():
    return queries.facets()


@app.get("/api/dashboard")
def get_dashboard():
    return queries.dashboard()


@app.get("/api/documents")
def documents(
    authority: Optional[str] = None,
    region: Optional[str] = None,
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
    area: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
):
    return queries.list_documents(
        authority=authority, region=region, category=category,
        risk_level=risk_level, area=area, q=q, limit=limit, offset=offset,
    )


@app.get("/api/documents/{doc_id}")
def document(doc_id: int):
    doc = queries.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.post("/api/documents/{doc_id}/interpret")
def interpret(doc_id: int):
    from ..nlp.interpret import interpret_one

    s = get_settings()
    if not s.claude_enabled:
        raise HTTPException(status_code=400, detail="ANTHROPIC_API_KEY not set")
    try:
        data = interpret_one(doc_id, s)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"document_id": doc_id, "interpretation": data}


class SearchReq(BaseModel):
    query: str
    top_k: int = 10
    authority: Optional[str] = None
    region: Optional[str] = None


@app.post("/api/search")
def search(req: SearchReq):
    from ..search.semantic import search_documents

    results = search_documents(
        req.query, top_k=req.top_k, authority=req.authority, region=req.region
    )
    return {"query": req.query, "results": results}


class AskReq(BaseModel):
    question: str
    top_k: int = 8
    authority: Optional[str] = None
    region: Optional[str] = None


@app.post("/api/ask")
def ask(req: AskReq):
    return rag.ask(
        req.question, top_k=req.top_k, authority=req.authority, region=req.region
    )
