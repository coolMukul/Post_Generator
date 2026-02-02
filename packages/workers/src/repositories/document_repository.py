"""Document repository for database operations."""
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
import json
import psycopg
from psycopg.rows import dict_row
from urllib.parse import urlparse, unquote


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
        # Ensure title and metadata defaults
        if not title:
            parsed = urlparse(url)
            candidate = parsed.path.split('/')[-1] or parsed.netloc
            title = unquote(candidate) or 'Untitled'

        if metadata is None:
            metadata = {}

        # Generate checksum from URL
        checksum = hashlib.sha256(url.encode()).hexdigest()

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

                # Insert new document
                cur.execute(
                    """
                    INSERT INTO documents (source_url, title, checksum, metadata, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (url, title, checksum, json.dumps(metadata or {}), datetime.now())
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
                cur.execute(
                    """
                    UPDATE documents
                    SET metadata = %s
                    WHERE id = %s
                    RETURNING *
                    """,
                    (json.dumps(metadata), document_id)
                )
                result = cur.fetchone()
                conn.commit()
                return dict(result) if result else None
