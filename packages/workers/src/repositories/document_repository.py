"""Document repository for database operations (UUID-based schema)."""
import hashlib
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urlparse, unquote

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)


class DocumentRepository:
    """Repository for document CRUD operations."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def create_document(
        self,
        url: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new document with SHA-256 deduplication."""
        if not title:
            parsed = urlparse(url)
            candidate = parsed.path.split("/")[-1] or parsed.netloc
            title = unquote(candidate) or "Untitled"

        if metadata is None:
            metadata = {}

        checksum = hashlib.sha256(url.encode()).hexdigest()

        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM documents WHERE checksum = %s",
                    (checksum,),
                )
                existing = cur.fetchone()
                if existing:
                    logger.info("Document already exists: %s", existing["id"])
                    return dict(existing)

                cur.execute(
                    """
                    INSERT INTO documents (title, source_url, checksum, metadata, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (title, url, checksum, json.dumps(metadata), datetime.now()),
                )
                document = cur.fetchone()
                conn.commit()
                logger.info("Document created: %s", document["id"])
                return dict(document)

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by UUID."""
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
                result = cur.fetchone()
                return dict(result) if result else None

    def get_document_by_checksum(self, checksum: str) -> Optional[Dict[str, Any]]:
        """Get document by checksum."""
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM documents WHERE checksum = %s", (checksum,))
                result = cur.fetchone()
                return dict(result) if result else None

    def update_document_metadata(
        self,
        document_id: str,
        metadata: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update document metadata."""
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE documents
                    SET metadata = %s
                    WHERE id = %s
                    RETURNING *
                    """,
                    (json.dumps(metadata), document_id),
                )
                result = cur.fetchone()
                conn.commit()
                return dict(result) if result else None

    def count_documents(self) -> int:
        """Return the total number of documents."""
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS count FROM documents")
                row = cur.fetchone()
                return row["count"] if row else 0

    def link_document_to_project(
        self,
        document_id: str,
        project_key: str,
    ) -> str:
        """Link a document to a project via project_documents. Returns project_document_id."""
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM projects WHERE key = %s", (project_key,))
                project = cur.fetchone()
                if not project:
                    raise ValueError(f"Project with key '{project_key}' not found")

                cur.execute(
                    """
                    INSERT INTO project_documents (project_id, document_id, status, added_at)
                    VALUES (%s, %s, 'pending', NOW())
                    ON CONFLICT (project_id, document_id) DO UPDATE SET status = 'pending'
                    RETURNING id
                    """,
                    (project["id"], document_id),
                )
                pd_row = cur.fetchone()
                conn.commit()
                logger.info(
                    "Linked document %s to project '%s' -> project_document_id=%s",
                    document_id,
                    project_key,
                    pd_row["id"],
                )
                return str(pd_row["id"])

    def get_project_by_key(self, project_key: str) -> Optional[Dict[str, Any]]:
        """Fetch project record by key."""
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM projects WHERE key = %s", (project_key,))
                result = cur.fetchone()
                return dict(result) if result else None
