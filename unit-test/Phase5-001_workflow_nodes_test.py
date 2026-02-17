"""Phase 5 – Unit tests for workflow nodes.

Tests:
  - insight_extraction: rule-based extraction
  - draft_generation: template-based generation
  - citation_validation: validation logic
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "workers"))

from src.agents.workflows.insight_extraction import extract_insights
from src.agents.workflows.draft_generation import generate_draft
from src.agents.workflows.citation_validation import validate_citations


# ---------------------------------------------------------------
# Insight Extraction Tests
# ---------------------------------------------------------------
class TestInsightExtraction:
    def test_no_results(self):
        state = {"search_results": [], "steps_log": []}
        result = extract_insights(state)
        assert result["insights"] == []
        assert result["current_step"] == "insight_extraction"
        assert "insight_extraction" in result["steps_log"][0]

    def test_with_results(self):
        state = {
            "search_results": [
                {
                    "documentTitle": "AI Paper",
                    "content": "Deep learning has revolutionized NLP tasks with transformer architectures.",
                    "score": 0.85,
                },
                {
                    "documentTitle": "ML Study",
                    "content": "Reinforcement learning shows promise in robotics applications.",
                    "score": 0.5,
                },
                {
                    "documentTitle": "Low Score",
                    "content": "Irrelevant content.",
                    "score": 0.1,
                },
            ],
            "steps_log": [],
        }
        result = extract_insights(state)
        insights = result["insights"]
        assert len(insights) >= 2
        assert any("AI Paper" in i for i in insights)
        assert result["current_step"] == "insight_extraction"

    def test_preserves_existing_steps_log(self):
        state = {
            "search_results": [{"content": "test", "score": 0.5, "documentTitle": "T"}],
            "steps_log": ["retrieval: 1 results"],
        }
        result = extract_insights(state)
        assert len(result["steps_log"]) == 2


# ---------------------------------------------------------------
# Draft Generation Tests
# ---------------------------------------------------------------
class TestDraftGeneration:
    def test_no_insights(self):
        state = {"insights": [], "query": "test", "steps_log": []}
        result = generate_draft(state)
        assert result["draft"] == ""
        assert result["current_step"] == "draft_generation"

    def test_template_generation(self):
        state = {
            "insights": [
                "Transformers improved NLP accuracy by 15%",
                "Multi-head attention is key to success",
            ],
            "query": "transformer architectures",
            "steps_log": [],
        }
        result = generate_draft(state)
        draft = result["draft"]
        assert len(draft) > 0
        assert "transformer architectures" in draft
        assert "Transformers improved" in draft
        assert result["current_step"] == "draft_generation"

    def test_steps_log_updated(self):
        state = {
            "insights": ["Finding 1"],
            "query": "test",
            "steps_log": ["retrieval: ok"],
        }
        result = generate_draft(state)
        assert len(result["steps_log"]) == 2
        assert "draft_generation" in result["steps_log"][1]


# ---------------------------------------------------------------
# Citation Validation Tests
# ---------------------------------------------------------------
class TestCitationValidation:
    def test_no_results(self):
        state = {"search_results": [], "draft": "Some draft", "steps_log": []}
        result = validate_citations(state)
        assert result["citations"] == []
        assert len(result["validation_errors"]) > 0
        assert result["current_step"] == "citation_validation"

    def test_valid_citations(self):
        state = {
            "search_results": [
                {
                    "documentId": "doc-1",
                    "documentTitle": "Good Paper",
                    "chunkIndex": 0,
                    "content": "Relevant content about the topic.",
                    "score": 0.9,
                    "rankSource": "hybrid",
                    "metadata": {},
                },
            ],
            "draft": "As discussed in Good Paper, the topic is important.",
            "steps_log": [],
        }
        result = validate_citations(state)
        assert len(result["citations"]) == 1
        assert result["citations"][0]["document_title"] == "Good Paper"
        assert result["current_step"] == "citation_validation"

    def test_low_relevance_warning(self):
        state = {
            "search_results": [
                {
                    "documentId": "doc-1",
                    "documentTitle": "Weak Paper",
                    "chunkIndex": 0,
                    "content": "Content.",
                    "score": 0.05,
                    "rankSource": "keyword",
                    "metadata": {},
                },
            ],
            "draft": "Draft text",
            "steps_log": [],
        }
        result = validate_citations(state)
        errors = result["validation_errors"]
        assert any("low relevance" in e.lower() for e in errors)

    def test_missing_title_warning(self):
        state = {
            "search_results": [
                {
                    "documentId": "doc-1",
                    "chunkIndex": 0,
                    "content": "Content.",
                    "score": 0.5,
                    "rankSource": "vector",
                    "metadata": {},
                },
            ],
            "draft": "Draft text",
            "steps_log": [],
        }
        result = validate_citations(state)
        errors = result["validation_errors"]
        assert any("missing document titles" in e.lower() for e in errors)

    def test_unreferenced_docs_warning(self):
        state = {
            "search_results": [
                {
                    "documentId": "doc-1",
                    "documentTitle": "Obscure Paper",
                    "chunkIndex": 0,
                    "content": "Content about something.",
                    "score": 0.7,
                    "rankSource": "hybrid",
                    "metadata": {},
                },
            ],
            "draft": "This draft does not mention any sources at all.",
            "steps_log": [],
        }
        result = validate_citations(state)
        errors = result["validation_errors"]
        assert any("reference" in e.lower() for e in errors)
