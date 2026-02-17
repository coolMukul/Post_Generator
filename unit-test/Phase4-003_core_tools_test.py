"""Phase 4 – Unit tests for core agent tools.

Tests:
  - cite_source: citation formatting
  - cite_sources_from_results: batch citation
  - summarize_chunk: context summary passthrough
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "workers"))

from src.agents.tools.cite_source import cite_source, cite_sources_from_results
from src.agents.tools.summarize_chunk import summarize_chunk


# ---------------------------------------------------------------
# cite_source tests
# ---------------------------------------------------------------
class TestCiteSource:
    def test_basic_citation(self):
        result = cite_source(
            document_id="doc-123",
            document_title="Test Paper",
            chunk_index=0,
            content_snippet="This is the content of the chunk.",
            score=0.85,
            rank_source="hybrid",
        )
        assert result["document_id"] == "doc-123"
        assert result["document_title"] == "Test Paper"
        assert result["chunk_index"] == 0
        assert result["relevance_score"] == 0.85
        assert result["rank_source"] == "hybrid"
        assert "This is the content" in result["snippet"]

    def test_untitled_default(self):
        result = cite_source(document_id="doc-456")
        assert result["document_title"] == "Untitled"
        assert result["chunk_index"] == 0
        assert result["relevance_score"] == 0.0

    def test_long_snippet_truncation(self):
        long_content = "x" * 300
        result = cite_source(
            document_id="doc-789",
            content_snippet=long_content,
        )
        assert len(result["snippet"]) <= 153  # 150 + "..."
        assert result["snippet"].endswith("...")

    def test_metadata_extraction(self):
        result = cite_source(
            document_id="doc-abc",
            metadata={"url": "https://example.com", "author": "John Doe", "published_date": "2025-01-01"},
        )
        assert result["url"] == "https://example.com"
        assert result["author"] == "John Doe"
        assert result["published_date"] == "2025-01-01"


class TestCiteSourcesFromResults:
    def test_batch_citation(self):
        results = [
            {
                "documentId": "doc-1",
                "documentTitle": "Paper A",
                "chunkIndex": 0,
                "content": "Content A",
                "score": 0.9,
                "rankSource": "vector",
                "metadata": {},
            },
            {
                "documentId": "doc-2",
                "documentTitle": "Paper B",
                "chunkIndex": 1,
                "content": "Content B",
                "score": 0.7,
                "rankSource": "keyword",
                "metadata": {},
            },
        ]
        citations = cite_sources_from_results(results)
        assert len(citations) == 2
        assert citations[0]["document_title"] == "Paper A"
        assert citations[1]["relevance_score"] == 0.7

    def test_empty_results(self):
        citations = cite_sources_from_results([])
        assert citations == []

    def test_snake_case_keys(self):
        results = [
            {
                "document_id": "doc-1",
                "document_title": "Snake Paper",
                "chunk_index": 2,
                "content": "Snake content",
                "score": 0.5,
                "rank_source": "hybrid",
                "metadata": {},
            },
        ]
        citations = cite_sources_from_results(results)
        assert len(citations) == 1
        assert citations[0]["document_title"] == "Snake Paper"


# ---------------------------------------------------------------
# summarize_chunk tests (only context_summary passthrough, no LLM)
# ---------------------------------------------------------------
class TestSummarizeChunk:
    def test_context_summary_passthrough(self):
        result = summarize_chunk(
            content="Full chunk content that is very long...",
            context_summary="Pre-computed summary from ingestion",
        )
        assert result["method"] == "context_summary"
        assert result["summary"] == "Pre-computed summary from ingestion"
        assert result["original_length"] > 0

    def test_context_summary_truncation(self):
        long_summary = "x" * 1000
        result = summarize_chunk(
            content="anything",
            context_summary=long_summary,
            max_length=100,
        )
        assert len(result["summary"]) <= 100
