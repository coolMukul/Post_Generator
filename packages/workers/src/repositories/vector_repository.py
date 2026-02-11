"""Vector repository for document_vectors table operations."""
import logging
from typing import List, Optional, Dict, Any
import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector

logger = logging.getLogger(__name__)


class VectorRepository:
    """Repository for vector CRUD and search operations against document_vectors."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def create_vector(
        self,
        project_document_id: str,
        chunk_index: int,
        content: str,
        embedding: List[float],
        context_summary: Optional[str] = None,
        token_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Insert a single vector into document_vectors."""
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO document_vectors
                        (project_document_id, chunk_index, content, context_summary,
                         embedding, token_count, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        project_document_id,
                        chunk_index,
                        content,
                        context_summary,
                        embedding,
                        token_count,
                        psycopg.types.json.Json(metadata or {}),
                    ),
                )
                vector = cur.fetchone()
                conn.commit()
                logger.info(
                    "Vector created: project_document_id=%s chunk_index=%s",
                    project_document_id,
                    chunk_index,
                )
                return dict(vector)

    def bulk_create_vectors(self, vectors: List[Dict[str, Any]]) -> int:
        """Bulk insert multiple vectors into document_vectors."""
        if not vectors:
            return 0

        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                values = [
                    (
                        v["project_document_id"],
                        v["chunk_index"],
                        v["content"],
                        v.get("context_summary"),
                        v["embedding"],
                        v.get("token_count"),
                        psycopg.types.json.Json(v.get("metadata", {})),
                    )
                    for v in vectors
                ]
                cur.executemany(
                    """
                    INSERT INTO document_vectors
                        (project_document_id, chunk_index, content, context_summary,
                         embedding, token_count, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    values,
                )
                conn.commit()
                logger.info("Bulk inserted %d vectors", len(vectors))
                return len(vectors)

    def similarity_search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        project_document_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Cosine similarity search with document title join."""
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                if project_document_id:
                    cur.execute(
                        """
                        SELECT dv.id, dv.project_document_id, dv.chunk_index,
                               dv.content, dv.context_summary, dv.token_count,
                               dv.metadata,
                               1 - (dv.embedding <=> %s::vector) AS similarity,
                               d.title AS document_title,
                               d.id AS document_id
                        FROM document_vectors dv
                        JOIN project_documents pd ON dv.project_document_id = pd.id
                        JOIN documents d ON pd.document_id = d.id
                        WHERE dv.project_document_id = %s
                        ORDER BY dv.embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (query_embedding, project_document_id, query_embedding, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT dv.id, dv.project_document_id, dv.chunk_index,
                               dv.content, dv.context_summary, dv.token_count,
                               dv.metadata,
                               1 - (dv.embedding <=> %s::vector) AS similarity,
                               d.title AS document_title,
                               d.id AS document_id
                        FROM document_vectors dv
                        JOIN project_documents pd ON dv.project_document_id = pd.id
                        JOIN documents d ON pd.document_id = d.id
                        ORDER BY dv.embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (query_embedding, query_embedding, limit),
                    )
                return [dict(row) for row in cur.fetchall()]

    def keyword_search(
        self,
        query_text: str,
        limit: int = 10,
        project_document_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Full-text keyword search using PostgreSQL ts_vector / ts_query."""
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                if project_document_id:
                    cur.execute(
                        """
                        SELECT dv.id, dv.project_document_id, dv.chunk_index,
                               dv.content, dv.context_summary, dv.token_count,
                               dv.metadata,
                               ts_rank_cd(
                                   to_tsvector('english', dv.content),
                                   plainto_tsquery('english', %s)
                               ) AS rank,
                               d.title AS document_title,
                               d.id AS document_id
                        FROM document_vectors dv
                        JOIN project_documents pd ON dv.project_document_id = pd.id
                        JOIN documents d ON pd.document_id = d.id
                        WHERE to_tsvector('english', dv.content)
                              @@ plainto_tsquery('english', %s)
                          AND dv.project_document_id = %s
                        ORDER BY rank DESC
                        LIMIT %s
                        """,
                        (query_text, query_text, project_document_id, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT dv.id, dv.project_document_id, dv.chunk_index,
                               dv.content, dv.context_summary, dv.token_count,
                               dv.metadata,
                               ts_rank_cd(
                                   to_tsvector('english', dv.content),
                                   plainto_tsquery('english', %s)
                               ) AS rank,
                               d.title AS document_title,
                               d.id AS document_id
                        FROM document_vectors dv
                        JOIN project_documents pd ON dv.project_document_id = pd.id
                        JOIN documents d ON pd.document_id = d.id
                        WHERE to_tsvector('english', dv.content)
                              @@ plainto_tsquery('english', %s)
                        ORDER BY rank DESC
                        LIMIT %s
                        """,
                        (query_text, query_text, limit),
                    )
                return [dict(row) for row in cur.fetchall()]

    def get_vectors_by_document(self, project_document_id: str) -> List[Dict[str, Any]]:
        """Get all vectors for a given project_document_id."""
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM document_vectors
                    WHERE project_document_id = %s
                    ORDER BY chunk_index
                    """,
                    (project_document_id,),
                )
                return [dict(row) for row in cur.fetchall()]

    def delete_vectors_by_document(self, project_document_id: str) -> int:
        """Delete all vectors for a given project_document_id."""
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM document_vectors WHERE project_document_id = %s",
                    (project_document_id,),
                )
                deleted_count = cur.rowcount
                conn.commit()
                logger.info(
                    "Deleted %d vectors for project_document_id=%s",
                    deleted_count,
                    project_document_id,
                )
                return deleted_count
