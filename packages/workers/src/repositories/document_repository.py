"""Document repository for database operations."""
import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any
import psycopg
from psycopg.rows import dict_row


class DocumentRepository:
    """Repository for document operations."""

    def __init__(self, connection_string: str):
        """Initialize repository with database connection."""
        self.connection_string = connection_string

    def create_document(
        self,
        url: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new document in the database.

        Args:
            url: Document URL
            title: Optional document title
            metadata: Optional metadata dictionary

        Returns:
            Created document dictionary
        """
        # Generate checksum from URL
        checksum = hashlib.sha256(url.encode()).hexdigest()

        # Ensure title is not null to satisfy DB NOT NULL constraint
        # Prefer provided title, then metadata.title, then fall back to the URL
        title_value = title if title is not None else None
        try:
            if (title_value is None) and metadata and isinstance(metadata, dict):
                title_value = metadata.get('title')
        except Exception:
            title_value = title_value

        if title_value is None:
            title_value = url or ''

        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Check if document already exists
                cur.execute(
                    "SELECT * FROM documents WHERE checksum = %s",
                    (checksum,)
                )
                existing = cur.fetchone()

                if existing:
                    print(f"Document already exists: {existing['id']}")
                    return dict(existing)

                # Insert new document - serialize metadata to JSON and cast to jsonb
                metadata_json = json.dumps(metadata or {})
                cur.execute(
                    """
                    INSERT INTO documents (source_url, title, checksum, metadata, created_at)
                    VALUES (%s, %s, %s, %s::jsonb, %s)
                    RETURNING *
                    """,
                    (url, title_value, checksum, metadata_json, datetime.now())
                )
                document = cur.fetchone()
                conn.commit()

                print(f"Document created: {document['id']}")
                return dict(document)

    def get_document(self, document_id: int) -> Optional[Dict[str, Any]]:
        """
        Get document by ID.

        Args:
            document_id: Document ID

        Returns:
            Document dictionary or None
        """
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
                result = cur.fetchone()
                return dict(result) if result else None

    def get_document_by_checksum(self, checksum: str) -> Optional[Dict[str, Any]]:
        """
        Get document by checksum.

        Args:
            checksum: Document checksum

        Returns:
            Document dictionary or None
        """
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM documents WHERE checksum = %s", (checksum,))
                result = cur.fetchone()
                return dict(result) if result else None

    def update_document_metadata(
        self,
        document_id: int,
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update document metadata.

        Args:
            document_id: Document ID
            metadata: New metadata dictionary

        Returns:
            Updated document dictionary or None
        """
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Serialize metadata and cast to jsonb on update
                metadata_json = json.dumps(metadata)
                cur.execute(
                    """
                    UPDATE documents
                    SET metadata = %s::jsonb
                    WHERE id = %s
                    RETURNING *
                    """,
                    (metadata_json, document_id)
                )
                result = cur.fetchone()
                conn.commit()
                return dict(result) if result else None
