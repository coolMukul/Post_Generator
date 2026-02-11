# Post Generator API (Python)

This package contains a minimal FastAPI-based replacement for the previous TypeScript API. It provides a small skeleton for Phase 3 (hybrid_search).

Run locally with pip (recommended in a venv):

```bash
python -m pip install -r requirements.txt
API_PORT=8000 python -m app.main
```

Endpoints:
- `GET /health` — basic health check
- `POST /hybrid_search/query` — placeholder hybrid search endpoint

Further work: hook this service to the worker/vector store and extend endpoints as needed.
