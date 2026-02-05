"""
Hybrid Retrieval Repository

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
import logging


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
class HybridRetrievalConfig:
    """Configuration for hybrid retrieval."""
    default_limit: int = 20
    default_min_score: float = 0.3
    default_vector_weight: float = 0.7
    default_keyword_weight: float = 0.3
    rrf_k: int = 60
    vector_min_score: float = 0.7
    enable_query_expansion: bool = True


class HybridRetrievalRepository:
    """
    Repository for hybrid retrieval operations.

    Combines vector similarity and keyword search for optimal retrieval.
    Uses Reciprocal Rank Fusion (RRF) for intelligent result merging.
    """

    def __init__(
        self,
        connection_string: str,
        config: Optional[HybridRetrievalConfig] = None
    ):
        """
        Initialize hybrid retrieval repository.

        Args:
            connection_string: PostgreSQL connection string
            config: Optional retrieval configuration
        """
        self.connection_string = connection_string
        self.config = config or HybridRetrievalConfig()

    def hybrid_retrieval(
        self,
        query: str,
        query_embedding: List[float],
        project_key: str = 'researchpaper',
        limit: int = None,
        min_score: float = None,
        vector_weight: float = None,
        keyword_weight: float = None,
        rrf_k: int = None,
        debug: bool = False
    ) -> Any:
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

        if debug:
            # Return intermediate data for debugging
            return {
                'vector_results': [ {'id': vid, 'rank': rank} for vid, rank in vector_results ],
                'keyword_results': [ {'id': kid, 'rank': rank} for kid, rank in keyword_results ],
                'merged_count': len(merged_results),
                'merged_results': [ {'id': r.id, 'score': r.score, 'rank_source': r.rank_source} for r in merged_results ],
                'filtered_count': len(filtered_results),
                'filtered_results': [ {'id': r.id, 'score': r.score, 'rank_source': r.rank_source} for r in filtered_results ],
                'final': [r for r in filtered_results[:limit]]
            }

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

        logger = logging.getLogger(__name__)
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                sql = (
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
                    """
                )

                logger.info("📝 [VECTOR SEARCH] SQL prepared")
                logger.info("📝 [VECTOR SEARCH] Params: embedding=%s, project=%s, min_score=%s, limit=%s", embedding_str[:120], project_key, min_score, limit)

                # Check counts
                try:
                    cur.execute("SELECT COUNT(*) as count FROM document_vectors")
                    dv_count = cur.fetchone()
                    logger.info("📊 [VECTOR SEARCH] document_vectors count: %s", dv_count['count'])
                except Exception:
                    logger.warning("⚠️  [VECTOR SEARCH] Could not read document_vectors count")

                try:
                    cur.execute(sql, (embedding_str, project_key, embedding_str, min_score, embedding_str, limit))
                except Exception as e:
                    logger.error("❌ [VECTOR SEARCH] SQL execution failed: %s", str(e), exc_info=True)
                    return []

                results = cur.fetchall()
                logger.info("📊 [VECTOR SEARCH] Raw rows returned: %d", len(results))
                for idx, row in enumerate(results[:3]):
                    logger.info("📄 [VECTOR SEARCH] Row %d: id=%s title=%s score=%s", idx+1, row.get('id'), (row.get('document_title') or '')[:80], row.get('score'))

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

    def keyword_search_fallback(
        self,
        query: str,
        project_key: str,
        limit: int = 20,
        min_score: float = 0.3,
        debug: bool = False,
        disable_fulltext: bool = False,
        disable_ilike: bool = False,
        disable_token: bool = False
    ) -> Any:
        """
        Perform simple keyword search as a fallback when embeddings aren't available.
        Searches against documents table using title and metadata.

        Args:
            query: Search query text
            project_key: Project to search within (not used in fallback)
            limit: Maximum number of results
            min_score: Minimum score threshold (0-1)

        Returns:
            List of result dictionaries
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔎 [KEYWORD SEARCH] Starting search for: '{query}'")
        logger.info(f"🔎 [KEYWORD SEARCH] Parameters: limit={limit}, min_score={min_score}, project_key={project_key}")
        
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                sql_query = """
                    SELECT 
                        d.id,
                        d.id as document_id,
                        0 as chunk_index,
                        COALESCE(d.title, '') as content,
                        d.title as document_title,
                        NULL as context_summary,
                        d.metadata,
                        ts_rank_cd(
                            to_tsvector('english', COALESCE(d.title, '') || ' ' || COALESCE(d.metadata::text, '')),
                            plainto_tsquery('english', %s)
                        ) as score
                    FROM documents d
                    WHERE to_tsvector('english', COALESCE(d.title, '') || ' ' || COALESCE(d.metadata::text, ''))
                        @@ plainto_tsquery('english', %s)
                    ORDER BY score DESC
                    LIMIT %s
                """
                
                logger.info(f"📝 [KEYWORD SEARCH] SQL Query: {sql_query.strip()}")
                logger.info(f"📝 [KEYWORD SEARCH] Parameters: query='{query}', limit={limit}")
                
                # First, check if documents table exists and has data
                cur.execute("SELECT COUNT(*) as count FROM documents")
                doc_count = cur.fetchone()
                logger.info(f"📊 [KEYWORD SEARCH] Total documents in table: {doc_count['count']}")

                rows = []

                match_count = {'count': 0}
                # Check full-text matches unless explicitly disabled
                if not disable_fulltext:
                    cur.execute("""
                        SELECT COUNT(*) as count FROM documents d
                        WHERE to_tsvector('english', COALESCE(d.title, '') || ' ' || COALESCE(d.metadata::text, ''))
                            @@ plainto_tsquery('english', %s)
                    """, (query,))
                    match_count = cur.fetchone()
                    logger.info(f"📊 [KEYWORD SEARCH] Documents matching query: {match_count['count']}")
                else:
                    logger.info("📊 [KEYWORD SEARCH] Full-text matching disabled by debug flag")

                # If no matches (or full-text disabled), attempt fallbacks
                if match_count['count'] == 0:
                    cur.execute("SELECT id, title, metadata FROM documents LIMIT 5")
                    sample_docs = cur.fetchall()
                    logger.warning(f"⚠️  [KEYWORD SEARCH] No full-text matches found! Sample documents:")
                    for doc in sample_docs:
                        logger.warning(f"   - ID: {doc['id']}, Title: {doc.get('title', 'N/A')}")

                    # Try a safe ILIKE substring fallback against title and metadata->>'title'
                    # ILIKE fallback unless disabled
                    if not disable_ilike:
                        try:
                            ilike_sql = """
                                SELECT
                                    d.id,
                                    d.id as document_id,
                                    0 as chunk_index,
                                    COALESCE(d.title, '') as content,
                                    d.title as document_title,
                                    NULL as context_summary,
                                    d.metadata,
                                    1.0 as score
                                FROM documents d
                                WHERE COALESCE(d.title, '') ILIKE %s
                                   OR COALESCE(d.metadata->>'title', '') ILIKE %s
                                LIMIT %s
                            """

                            pattern = f"%{query}%"
                            logger.info("📝 [KEYWORD SEARCH] Running ILIKE fallback with pattern=%s", pattern)
                            cur.execute(ilike_sql, (pattern, pattern, limit))
                            rows = cur.fetchall()
                            logger.info("📊 [KEYWORD SEARCH] ILIKE fallback rows returned: %d", len(rows))
                        except Exception as e:
                            logger.error("❌ [KEYWORD SEARCH] ILIKE fallback failed: %s", str(e), exc_info=True)
                    else:
                        logger.info("📊 [KEYWORD SEARCH] ILIKE fallback disabled by debug flag")

                    # If still no rows, try individual token matching against metadata::text unless disabled
                    if not rows and not disable_token:
                        try:
                            tokens = [w.strip() for w in re.split(r"\s+", query) if w.strip()]
                            if tokens:
                                # Build dynamic WHERE clause: metadata::text ILIKE %token% OR title ILIKE %token%
                                where_clauses = []
                                params = []
                                for tok in tokens:
                                    where_clauses.append("COALESCE(d.metadata::text, '') ILIKE %s")
                                    params.append(f"%{tok}%")
                                    where_clauses.append("COALESCE(d.title, '') ILIKE %s")
                                    params.append(f"%{tok}%")

                                meta_sql = f"""
                                    SELECT
                                        d.id,
                                        d.id as document_id,
                                        0 as chunk_index,
                                        COALESCE(d.title, '') as content,
                                        d.title as document_title,
                                        NULL as context_summary,
                                        d.metadata,
                                        1.0 as score
                                    FROM documents d
                                    WHERE ({' OR '.join(where_clauses)})
                                    LIMIT %s
                                """
                                params.append(limit)
                                logger.info("📝 [KEYWORD SEARCH] Running metadata::text token fallback with tokens=%s", tokens)
                                cur.execute(meta_sql, tuple(params))
                                rows = cur.fetchall()
                                logger.info("📊 [KEYWORD SEARCH] metadata::text token fallback rows returned: %d", len(rows))
                        except Exception as e:
                            logger.error("❌ [KEYWORD SEARCH] metadata token fallback failed: %s", str(e), exc_info=True)
                    else:
                        if not disable_token:
                            logger.info("📊 [KEYWORD SEARCH] metadata::text token fallback skipped because prior fallback returned rows")
                        else:
                            logger.info("📊 [KEYWORD SEARCH] metadata::text token fallback disabled by debug flag")
                else:
                    # Execute the main search query when full-text matches exist
                    cur.execute(sql_query, (query, query, limit))
                    rows = cur.fetchall()
                
                logger.info(f"📊 [KEYWORD SEARCH] Raw rows returned: {len(rows)}")
                # Build debug payload pieces
                debug_payload = {
                    'doc_count': doc_count['count'],
                    'fulltext_match_count': match_count['count'] if isinstance(match_count, dict) else match_count,
                    'ilike_count': len(rows) if rows else 0,
                    'rows_sample': [dict(row) for row in rows[:5]]
                }
                
                if rows:
                    for idx, row in enumerate(rows[:3]):  # Log first 3 for debugging
                        logger.info(f"📄 [KEYWORD SEARCH] Row {idx+1}: id={row['id']}, title={row.get('document_title', 'N/A')[:50]}, score={row.get('score', 0)}")
                
                # Normalize scores and filter by min_score
                # Coerce DB numeric types (which may be Decimal) to float to avoid
                # unsupported operand type errors when dividing.
                max_score = float(max((row['score'] for row in rows), default=1.0))
                logger.info(f"📊 [KEYWORD SEARCH] Max score: {max_score}")

                results = []
                for row in rows:
                    raw_score = row.get('score') or 0.0
                    try:
                        score_float = float(raw_score)
                    except Exception:
                        score_float = float(str(raw_score))

                    normalized_score = score_float / max_score if max_score > 0 else 0.0

                    logger.debug(f"🔢 [KEYWORD SEARCH] Doc {row['id']}: raw_score={raw_score}, normalized={normalized_score}, min_score={min_score}")
                    
                    if normalized_score >= min_score:
                        # Parse metadata if it's a string
                        metadata = row.get('metadata')
                        if isinstance(metadata, str):
                            try:
                                import json
                                metadata = json.loads(metadata)
                            except:
                                metadata = {}
                        elif metadata is None:
                            metadata = {}
                        
                        results.append({
                            'id': str(row['id']),
                            'document_id': str(row['document_id']),
                            'chunk_index': row['chunk_index'],
                            'content': row['content'] or '',
                            'context_summary': row['context_summary'],
                            'score': normalized_score,
                            'rank_source': 'keyword',
                            'document_title': row['document_title'] or '',
                            'metadata': metadata
                        })
                    else:
                        logger.debug(f"❌ [KEYWORD SEARCH] Filtered out doc {row['id']} (score {normalized_score} < {min_score})")
                
                logger.info(f"✅ [KEYWORD SEARCH] Returning {len(results)} results after filtering")
                if debug:
                    return {
                        'debug': True,
                        'query': query,
                        'project_key': project_key,
                        'limit': limit,
                        'min_score': min_score,
                        'disable_fulltext': disable_fulltext,
                        'disable_ilike': disable_ilike,
                        'disable_token': disable_token,
                        'doc_count': doc_count['count'],
                        'fulltext_match_count': match_count['count'] if isinstance(match_count, dict) else match_count,
                        'returned_rows': [
                            {
                                'id': str(row['id']),
                                'title': row.get('document_title'),
                                'raw_score': float(row.get('score') or 0.0) if row.get('score') is not None else 0.0,
                                'metadata': row.get('metadata')
                            } for row in rows
                        ],
                        'filtered_results': results
                    }

                return results
