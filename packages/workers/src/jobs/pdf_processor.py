# REMOVED: PDF processing is out of scope for Phase 3 hybrid_search.
# This file is retained as a placeholder in case PDF processing is
# reintroduced later. Hybrid search functionality should rely on the
# repositories (vector_repository, document_repository) and the
# HybridWorker in worker.py.

async def process_pdf_job(*args, **kwargs):
    raise NotImplementedError("PDF processing removed for Phase 3. Use HybridWorker.")
