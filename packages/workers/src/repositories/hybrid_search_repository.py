"""
Hybrid Search Repository

Implements hybrid retrieval combining:
1. Vector similarity search (semantic) using pgvector
2. BM25 keyword search (lexical) using PostgreSQL full-text search
3. Reciprocal Rank Fusion (RRF) for intelligent result merging

This implementation includes:
- Configurable weights for vector vs keyword search
- Score normalization for interpretability
- Query expansion for better keyword matching
- Result deduplication and ranking
- Project-based filtering
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import psycopg
from psycopg.rows import dict_row
import re


@dataclass
class SearchResult:
    """Represents a single search result."""
    id: str
    document_id: str
    chunk_index: int
    content: str
    context_summary: Optional[str]
    score: float
    metadata: Dict[str, Any]
    rank_source: str  # 'vector', 'keyword', or 'hybrid'
    document_title: Optional[str] = None


@dataclass
class HybridSearchConfig:
    """Configuration for hybrid search."""
    default_limit: int = 20
    default_min_score: float = 0.3
    default_vector_weight: float = 0.7
    default_keyword_weight: float = 0.3
    rrf_k: int = 60
    vector_min_score: float = 0.7
    enable_query_expansion: bool = True


class HybridSearchRepository:
    """
    Repository for hybrid search operations.

    Combines vector similarity and keyword search for optimal retrieval.
    Uses Reciprocal Rank Fusion (RRF) for intelligent result merging.
    """

    def __init__(
        self,
        connection_string: str,
        config: Optional[HybridSearchConfig] = None
    ):
        """
        Initialize hybrid search repository.

        Args:
            connection_string: PostgreSQL connection string
            config: Optional search configuration
        """
        self.connection_string = connection_string
        self.config = config or HybridSearchConfig()

    def hybrid_retrieval(
        self,
        query: str,
        query_embedding: List[float],
        project_key: str = 'researchpaper',
        limit: int = None,
        min_score: float = None,
        vector_weight: float = None,
        keyword_weight: float = None,
        rrf_k: int = None
    ) -> List[SearchResult]:
        """
        Perform hybrid retrieval combining vector and keyword search.

        Args:
            query: Search query text
            query_embedding: Query embedding vector
            project_key: Project to search within
            limit: Maximum number of results
            min_score: Minimum score threshold
            vector_weight: Weight for vector search (0-1)
            keyword_weight: Weight for keyword search (0-1)
            rrf_k: RRF constant (higher = more conservative ranking)

        Returns:
            List of SearchResult objects sorted by hybrid score
        """
        # Use config defaults if not specified
        limit = limit or self.config.default_limit
        min_score = min_score or self.config.default_min_score
        vector_weight = vector_weight or self.config.default_vector_weight
        keyword_weight = keyword_weight or self.config.default_keyword_weight
        rrf_k = rrf_k or self.config.rrf_k

        # Fetch more results than needed for better RRF merging
        search_limit = limit * 2

        # Perform parallel searches
        vector_results = self._vector_search(
            query_embedding=query_embedding,
            project_key=project_key,
            limit=search_limit
        )

        keyword_results = self._keyword_search(
            query=query,
            project_key=project_key,
            limit=search_limit
        )

        # Merge using RRF
        merged_results = self._merge_with_rrf(
            vector_results=vector_results,
            keyword_results=keyword_results,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            rrf_k=rrf_k
        )

        # Filter and limit
        filtered_results = [
            r for r in merged_results
            if r.score >= min_score
        ]

        return filtered_results[:limit]

    def _vector_search(
        self,
        query_embedding: List[float],
        project_key: str,
        limit: int
    ) -> List[Tuple[str, int]]:
        """
        Perform vector similarity search using pgvector.

        Args:
            query_embedding: Query embedding vector
            project_key: Project to search within
            limit: Maximum number of results

        Returns:
            List of (result_id, rank) tuples
        """
        embedding_str = f"[{','.join(map(str, query_embedding))}]"
        min_score = self.config.vector_min_score

        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        dv.id,
                        pd.document_id,
                        dv.chunk_index,
                        dv.content,
                        dv.context_summary,
                        dv.metadata,
                        d.title as document_title,
                        1 - (dv.embedding <=> %s::vector) as score
                    FROM document_vectors dv
                    JOIN project_documents pd ON dv.project_document_id = pd.id
                    JOIN documents d ON pd.document_id = d.id
                    JOIN projects p ON pd.project_id = p.id
                    WHERE p.key = %s
                        AND pd.status = 'completed'
                        AND 1 - (dv.embedding <=> %s::vector) >= %s
                    ORDER BY dv.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (embedding_str, project_key, embedding_str, min_score, embedding_str, limit)
                )

                results = cur.fetchall()

                # Return as list of (id, rank) tuples
                return [
                    (row['id'], idx + 1)
                    for idx, row in enumerate(results)
                ]

    def _keyword_search(
        self,
        query: str,
        project_key: str,
        limit: int
    ) -> List[Tuple[str, int]]:
        """
        Perform BM25 keyword search using PostgreSQL full-text search.

        Args:
            query: Search query text
            project_key: Project to search within
            limit: Maximum number of results

        Returns:
            List of (result_id, rank) tuples
        """
        # Prepare tsquery with better tokenization
        ts_query = self._prepare_ts_query(query)

        if not ts_query:
            return []

        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        dv.id,
                        ts_rank_cd(
                            to_tsvector('english', dv.content || ' ' || COALESCE(dv.context_summary, '')),
                            to_tsquery('english', %s)
                        ) as score
                    FROM document_vectors dv
                    JOIN project_documents pd ON dv.project_document_id = pd.id
                    JOIN projects p ON pd.project_id = p.id
                    WHERE p.key = %s
                        AND pd.status = 'completed'
                        AND to_tsvector('english', dv.content || ' ' || COALESCE(dv.context_summary, ''))
                            @@ to_tsquery('english', %s)
                    ORDER BY score DESC
                    LIMIT %s
                    """,
                    (ts_query, project_key, ts_query, limit)
                )

                results = cur.fetchall()

                # Return as list of (id, rank) tuples
                return [
                    (row['id'], idx + 1)
                    for idx, row in enumerate(results)
                ]

    def _prepare_ts_query(self, query: str) -> str:
        """
        Prepare text for PostgreSQL tsquery with query expansion.

        Args:
            query: Raw search query

        Returns:
            Formatted tsquery string
        """
        # Remove special characters and extra whitespace
        cleaned = re.sub(r'[^\w\s]', ' ', query)
        words = cleaned.split()

        if not words:
            return ""

        # Basic query expansion: support both AND and OR
        # For multi-word queries, use OR for flexibility
        if self.config.enable_query_expansion and len(words) > 1:
            # Create flexible query: (word1 | word2 | word3)
            ts_query = ' | '.join(words)
        else:
            # Use AND for more precise matching
            ts_query = ' & '.join(words)

        return ts_query

    def _merge_with_rrf(
        self,
        vector_results: List[Tuple[str, int]],
        keyword_results: List[Tuple[str, int]],
        vector_weight: float,
        keyword_weight: float,
        rrf_k: int
    ) -> List[SearchResult]:
        """
        Merge results using Reciprocal Rank Fusion (RRF).

        RRF formula: score = sum(weight / (k + rank))
        Scores are normalized to 0-1 range for interpretability.

        Args:
            vector_results: Results from vector search (id, rank)
            keyword_results: Results from keyword search (id, rank)
            vector_weight: Weight for vector results
            keyword_weight: Weight for keyword results
            rrf_k: RRF constant

        Returns:
            List of SearchResult objects sorted by RRF score
        """
        # Build score map
        score_map: Dict[str, Dict[str, Any]] = {}

        # Add vector results
        for result_id, rank in vector_results:
            score_map[result_id] = {
                'vector_rank': rank,
                'keyword_rank': 0,
                'rank_source': 'vector'
            }

        # Add keyword results
        for result_id, rank in keyword_results:
            if result_id in score_map:
                score_map[result_id]['keyword_rank'] = rank
                score_map[result_id]['rank_source'] = 'hybrid'
            else:
                score_map[result_id] = {
                    'vector_rank': 0,
                    'keyword_rank': rank,
                    'rank_source': 'keyword'
                }

        # Calculate RRF scores
        max_rrf_score = 0.0
        for result_id, data in score_map.items():
            rrf_score = 0.0

            if data['vector_rank'] > 0:
                rrf_score += vector_weight / (rrf_k + data['vector_rank'])

            if data['keyword_rank'] > 0:
                rrf_score += keyword_weight / (rrf_k + data['keyword_rank'])

            data['rrf_score'] = rrf_score
            max_rrf_score = max(max_rrf_score, rrf_score)

        # Normalize scores to 0-1 range
        if max_rrf_score > 0:
            for data in score_map.values():
                data['normalized_score'] = data['rrf_score'] / max_rrf_score
        else:
            for data in score_map.values():
                data['normalized_score'] = 0.0

        # Fetch full result details
        result_ids = list(score_map.keys())
        full_results = self._fetch_result_details(result_ids)

        # Combine with scores
        merged_results = []
        for result in full_results:
            result_id = result['id']
            data = score_map.get(result_id)

            if data:
                merged_results.append(SearchResult(
                    id=result['id'],
                    document_id=result['document_id'],
                    chunk_index=result['chunk_index'],
                    content=result['content'],
                    context_summary=result['context_summary'],
                    score=data['normalized_score'],
                    metadata=result.get('metadata', {}),
                    rank_source=data['rank_source'],
                    document_title=result.get('document_title')
                ))

        # Sort by normalized score
        merged_results.sort(key=lambda x: x.score, reverse=True)

        return merged_results

    def _fetch_result_details(self, result_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch full details for result IDs.

        Args:
            result_ids: List of document_vector IDs

        Returns:
            List of result dictionaries
        """
        if not result_ids:
            return []

        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Use ANY to efficiently query multiple IDs
                cur.execute(
                    """
                    SELECT
                        dv.id,
                        pd.document_id,
                        dv.chunk_index,
                        dv.content,
                        dv.context_summary,
                        dv.metadata,
                        d.title as document_title
                    FROM document_vectors dv
                    JOIN project_documents pd ON dv.project_document_id = pd.id
                    JOIN documents d ON pd.document_id = d.id
                    WHERE dv.id = ANY(%s)
                    """,
                    (result_ids,)
                )

                return [dict(row) for row in cur.fetchall()]
