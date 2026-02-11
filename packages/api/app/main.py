from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import sys
from pathlib import Path
import logging

# Ensure the workers package (packages/workers/src) is importable
ROOT = Path(__file__).resolve().parents[3]
WORKERS_SRC = ROOT / 'packages' / 'workers' / 'src'
sys.path.insert(0, str(WORKERS_SRC))

try:
    from worker import HybridWorker
except Exception:
    HybridWorker = None

app = FastAPI(title="Post Generator API (Python)", version="0.1.0")


@app.on_event("startup")
async def _log_docs_urls():
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    display_host = "localhost" if host == "0.0.0.0" else host
    docs_url = f"http://{display_host}:{port}/docs"
    redoc_url = f"http://{display_host}:{port}/redoc"
    # Print so it appears clearly in the console logs
    print(f"Swagger UI: {docs_url}")
    print(f"ReDoc: {redoc_url}")


class EmbeddingRequest(BaseModel):
    embedding: List[float]
    top_k: Optional[int] = 10
    document_id: Optional[int] = None


class TextQueryRequest(BaseModel):
    text: str
    top_k: Optional[int] = 10
    document_id: Optional[int] = None


def _text_to_embedding(text: str, dim: int = 8) -> List[float]:
    """Deterministic text->embedding converter.

    This is a simple, deterministic converter (SHA256-based) to produce
    a numeric vector for passing to the worker. It is NOT a semantic
    embedding and should be replaced by a proper embedding service
    (OpenAI, etc.) when available.
    """
    import hashlib
    h = hashlib.sha256(text.encode('utf-8')).digest()
    vals: List[float] = []
    for i in range(dim):
        byte = h[i % len(h)]
        vals.append((byte / 255.0) * 2.0 - 1.0)
    return vals


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/hybrid_search/embedding")
async def hybrid_search_by_embedding(req: EmbeddingRequest):
    if HybridWorker is None:
        raise HTTPException(status_code=500, detail="HybridWorker not available")

    worker = HybridWorker()
    results = worker.similarity_search(req.embedding, limit=req.top_k or 10, document_id=req.document_id)
    return {"results": results, "query_embedding_len": len(req.embedding)}


@app.post("/hybrid_search/query")
async def hybrid_search_by_text(req: TextQueryRequest):
    if HybridWorker is None:
        raise HTTPException(status_code=500, detail="HybridWorker not available")

    # Convert text to embedding and delegate to worker
    embedding = _text_to_embedding(req.text)
    worker = HybridWorker()
    results = worker.similarity_search(embedding, limit=req.top_k or 10, document_id=req.document_id)
    return {"results": results, "query": req.text, "embedding_len": len(embedding)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("API_PORT", "8000")), reload=True)
