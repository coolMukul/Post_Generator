"""Business logic services.

Imports are lazy so that lightweight consumers (e.g. the API, which only
needs JobStore) don't pull in heavy dependencies like ``openai``.
"""


def __getattr__(name: str):
    if name == "JobStore":
        from .job_store import JobStore
        return JobStore
    if name == "EmbeddingService":
        from .embedding_service import EmbeddingService
        return EmbeddingService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["EmbeddingService", "JobStore"]
