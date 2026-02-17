"""ResearchAgent – uses Phase 3 hybrid_retrieve to research ingested documents.

Searches documents, extracts findings, assesses confidence, and
recommends next steps. Outputs follow the ResearchAgent JSON contract.

Console log format: [Agent:ResearchAgent][step:<step>] message
"""
import logging
from typing import Any, Dict, List

from ..models.agent_schemas import ManifestSchema
from .base_agent import BaseAgent
from .tools.search_papers import search_papers
from .tools.summarize_chunk import summarize_chunk
from .tools.cite_source import cite_sources_from_results

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """Concrete research agent that searches and analyzes ingested papers."""

    def __init__(self, manifest: ManifestSchema):
        super().__init__(manifest)
        self.register_tool("search_papers", search_papers)
        self.register_tool("summarize_chunk", summarize_chunk)

    def execute(self, run_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute research: search → summarize → cite → assess confidence.

        Input (validated against manifest input_schema):
            query: str (required)
            search_mode: str (default "hybrid")
            limit: int (default 10)
            min_score: float (default 0.0)
            document_id: str | None

        Output (ResearchAgent contract):
            job_id, top_documents, findings, risks_and_unknowns,
            recommended_next_steps, confidence (0-1)
        """
        query = input_data["query"]
        search_mode = input_data.get("search_mode", "hybrid")
        limit = input_data.get("limit", 10)
        min_score = input_data.get("min_score", 0.0)
        document_id = input_data.get("document_id")

        self.log("search", f"Searching for: {query!r}")
        search_result = self.call_tool("search_papers", {
            "query": query,
            "search_mode": search_mode,
            "limit": limit,
            "min_score": min_score,
            "document_id": document_id,
        })

        if search_result.error:
            raise RuntimeError(f"search_papers failed: {search_result.error}")

        output = search_result.output
        job_id = output.get("job_id", "")
        results = output.get("results", [])
        results_count = output.get("results_count", 0)

        self.log("analyze", f"Analyzing {results_count} search results")

        top_documents = self._extract_top_documents(results)
        findings = self._extract_findings(results)
        citations = cite_sources_from_results(results)
        confidence = self._assess_confidence(results, results_count)

        risks = self._identify_risks(results, results_count, confidence)
        next_steps = self._recommend_next_steps(results, results_count, confidence)

        self.log("complete", f"findings={len(findings)} confidence={confidence:.2f}")

        return {
            "job_id": job_id,
            "top_documents": top_documents,
            "findings": findings,
            "citations": citations,
            "risks_and_unknowns": risks,
            "recommended_next_steps": next_steps,
            "confidence": confidence,
        }

    def _extract_top_documents(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract top document summaries from search results."""
        seen_docs: Dict[str, Dict[str, Any]] = {}
        for r in results:
            doc_id = r.get("documentId", r.get("document_id", ""))
            if doc_id and doc_id not in seen_docs:
                seen_docs[doc_id] = {
                    "document_id": doc_id,
                    "title": r.get("documentTitle", r.get("document_title", "Untitled")),
                    "top_score": r.get("score", 0.0),
                    "chunk_count": 0,
                }
            if doc_id in seen_docs:
                seen_docs[doc_id]["chunk_count"] += 1
        return list(seen_docs.values())

    def _extract_findings(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract key finding strings from high-scoring results."""
        findings = []
        for r in results:
            score = r.get("score", 0.0)
            if score >= 0.3:
                title = r.get("documentTitle", r.get("document_title", "Unknown"))
                content = r.get("content", "")[:200]
                findings.append(
                    f"[score={score:.2f}] From '{title}': {content}"
                )
        return findings

    def _assess_confidence(self, results: List[Dict[str, Any]], count: int) -> float:
        """Compute a confidence score (0-1) based on result quality."""
        if count == 0:
            return 0.0

        scores = [r.get("score", 0.0) for r in results]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        top_score = max(scores) if scores else 0.0

        coverage_factor = min(count / 5.0, 1.0)
        quality_factor = (avg_score + top_score) / 2.0

        confidence = round(coverage_factor * quality_factor, 4)
        return min(1.0, max(0.0, confidence))

    def _identify_risks(self, results: List[Dict[str, Any]], count: int, confidence: float) -> List[str]:
        """Identify risks and unknowns based on result quality."""
        risks = []
        if count == 0:
            risks.append("No documents matched the query — knowledge base may lack relevant content")
        if confidence < 0.3:
            risks.append("Low confidence in results — consider broadening the query or ingesting more documents")
        if count > 0:
            low_score_count = sum(1 for r in results if r.get("score", 0) < 0.2)
            if low_score_count > count * 0.5:
                risks.append("Over half the results have low relevance scores")
        return risks

    def _recommend_next_steps(self, results: List[Dict[str, Any]], count: int, confidence: float) -> List[str]:
        """Recommend next steps based on research results."""
        steps = []
        if confidence >= 0.6:
            steps.append("Proceed to insight extraction with the top results")
        if confidence < 0.6 and count > 0:
            steps.append("Refine the search query for better precision")
            steps.append("Consider ingesting additional source documents")
        if count == 0:
            steps.append("Ingest relevant documents before re-running the search")
        steps.append("Review findings and citations for accuracy before using in content")
        return steps
