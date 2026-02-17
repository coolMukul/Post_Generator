"""Repository layer for database operations.

Imports are lazy so that lightweight consumers (e.g. the API) don't pull
in heavy dependencies like ``pgvector``.
"""


def __getattr__(name: str):
    if name == "DocumentRepository":
        from .document_repository import DocumentRepository
        return DocumentRepository
    if name == "VectorRepository":
        from .vector_repository import VectorRepository
        return VectorRepository
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["DocumentRepository", "VectorRepository"]
