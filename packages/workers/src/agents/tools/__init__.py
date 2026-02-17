"""Core agent tools for Phase 4.

Tools:
  - search_papers: Searches ingested documents via hybrid_retrieve (reuses Phase 3)
  - summarize_chunk: Summarizes a document chunk using the configured LLM
  - cite_source: Formats citation metadata for a given document/chunk
"""
from .search_papers import search_papers
from .summarize_chunk import summarize_chunk
from .cite_source import cite_source

__all__ = ["search_papers", "summarize_chunk", "cite_source"]
