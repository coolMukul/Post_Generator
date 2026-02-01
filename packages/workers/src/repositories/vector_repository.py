"""Vector repository for database operations."""
from typing import List, Optional, Dict, Any
import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector


class VectorRepository:
    """Repository for vector operations."""

    def __init__(self, connection_string: str):
        """Initialize repository with database connection."""
        self.connection_string = connection_string

    def create_vector(
        self,
        document_id: int,
        chunk_index: int,
        content: str,
        embedding: List[float],
        context_summary: Optional[str] = None,
        token_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new vector entry.

        Args:
            document_id: Related document ID
            chunk_index: Index of the chunk in the document
            content: Text content
            embedding: Vector embedding (1536 dimensions)
            context_summary: Optional context summary
            token_count: Optional token count

        Returns:
            Created vector dictionary
        """
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            # Register pgvector extension
            register_vector(conn)

            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO vectors (document_id, chunk_index, content, context_summary,
                                       embedding, token_count)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (document_id, chunk_index, content, context_summary, embedding, token_count)
                )
                vector = cur.fetchone()
                conn.commit()

                print(f"Vector created: document_id={document_id}, chunk_index={chunk_index}")
                return dict(vector)

    def bulk_create_vectors(
        self,
        vectors: List[Dict[str, Any]]
    ) -> int:
        """
        Bulk insert multiple vectors.

        Args:
            vectors: List of vector dictionaries with keys:
                    document_id, chunk_index, content, embedding,
                    context_summary (optional), token_count (optional)

        Returns:
            Number of vectors inserted
        """
        if not vectors:
            return 0

        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            register_vector(conn)

            with conn.cursor() as cur:
                # Prepare batch insert
                values = [
                    (
                        v['document_id'],
                        v['chunk_index'],
                        v['content'],
                        v.get('context_summary'),
                        v['embedding'],
                        v.get('token_count')
                    )
                    for v in vectors
                ]

                cur.executemany(
                    """
                    INSERT INTO vectors (document_id, chunk_index, content, context_summary,
                                       embedding, token_count)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    values
                )
                conn.commit()

                print(f"Bulk inserted {len(vectors)} vectors")
                return len(vectors)

    def similarity_search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        document_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search using cosine distance.

        Args:
            query_embedding: Query vector embedding
            limit: Maximum number of results
            document_id: Optional filter by document ID

        Returns:
            List of similar vectors with similarity scores
        """
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            register_vector(conn)

            with conn.cursor() as cur:
                if document_id:
                    cur.execute(
                        """
                        SELECT *,
                               1 - (embedding <=> %s::vector) as similarity
                        FROM vectors
                        WHERE document_id = %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (query_embedding, document_id, query_embedding, limit)
                    )
                else:
                    cur.execute(
                        """
                        SELECT *,
                               1 - (embedding <=> %s::vector) as similarity
                        FROM vectors
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (query_embedding, query_embedding, limit)
                    )

                results = cur.fetchall()
                return [dict(row) for row in results]

    def get_vectors_by_document(self, document_id: int) -> List[Dict[str, Any]]:
        """
        Get all vectors for a document.

        Args:
            document_id: Document ID

        Returns:
            List of vector dictionaries
        """
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM vectors
                    WHERE document_id = %s
                    ORDER BY chunk_index
                    """,
                    (document_id,)
                )
                results = cur.fetchall()
                return [dict(row) for row in results]

    def delete_vectors_by_document(self, document_id: int) -> int:
        """
        Delete all vectors for a document.

        Args:
            document_id: Document ID

        Returns:
            Number of vectors deleted
        """
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM vectors WHERE document_id = %s", (document_id,))
                deleted_count = cur.rowcount
                conn.commit()

                print(f"Deleted {deleted_count} vectors for document {document_id}")
                return deleted_count
