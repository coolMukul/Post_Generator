"""
Fix Duplicate Documents Script

Transfers metadata from newly migrated documents (without embeddings)
to old documents (with embeddings) and deletes the duplicates.

This ensures hybrid retrieval works with proper metadata.
"""

import os
import sys
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()

DB_URL = os.getenv('DATABASE_URL')
if not DB_URL:
    print("❌ ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)


def find_duplicate_pairs(conn):
    """Find duplicate documents by source_url."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT
                source_url,
                COUNT(*) as count,
                ARRAY_AGG(id ORDER BY created_at) as ids,
                ARRAY_AGG(title ORDER BY created_at) as titles,
                ARRAY_AGG(
                    CASE WHEN EXISTS (
                        SELECT 1 FROM project_documents pd
                        JOIN document_vectors dv ON dv.project_document_id = pd.id
                        WHERE pd.document_id = d.id
                    ) THEN 1 ELSE 0 END
                    ORDER BY created_at
                ) as has_embeddings
            FROM documents d
            WHERE source_url IS NOT NULL
            GROUP BY source_url
            HAVING COUNT(*) > 1
            ORDER BY source_url
        """)

        return [dict(row) for row in cur.fetchall()]


def get_document_details(conn, doc_id):
    """Get full document details."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT d.*,
                   COUNT(dv.id) as embedding_count
            FROM documents d
            LEFT JOIN project_documents pd ON pd.document_id = d.id
            LEFT JOIN document_vectors dv ON dv.project_document_id = pd.id
            WHERE d.id = %s
            GROUP BY d.id
        """, (doc_id,))

        return dict(cur.fetchone())


def transfer_metadata(conn, from_doc_id, to_doc_id):
    """Transfer metadata and title from one document to another."""
    with conn.cursor(row_factory=dict_row) as cur:
        # Get source metadata
        cur.execute("SELECT title, metadata FROM documents WHERE id = %s", (from_doc_id,))
        source = cur.fetchone()

        if not source:
            return False

        # Update target
        cur.execute("""
            UPDATE documents
            SET title = %s, metadata = %s
            WHERE id = %s
            RETURNING *
        """, (source['title'], source['metadata'], to_doc_id))

        result = cur.fetchone()
        conn.commit()

        return result is not None


def delete_document(conn, doc_id):
    """Delete a document (cascades to project_documents)."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        conn.commit()


def main():
    print("=" * 70)
    print("🔧 Fix Duplicate Documents Script")
    print("=" * 70)
    print()

    conn = psycopg.connect(DB_URL)
    print("✅ Connected to database")
    print()

    # Find duplicates
    print("🔍 Searching for duplicate documents...")
    duplicates = find_duplicate_pairs(conn)

    if not duplicates:
        print("✅ No duplicate documents found!")
        return

    print(f"Found {len(duplicates)} sets of duplicates:")
    print("-" * 70)

    for dup in duplicates:
        print(f"\n📄 Source URL: {dup['source_url']}")
        print(f"   Duplicate count: {dup['count']}")

        # Show details for each duplicate
        for i, doc_id in enumerate(dup['ids']):
            details = get_document_details(conn, doc_id)
            has_emb = "✅ YES" if details['embedding_count'] > 0 else "❌ NO"

            print(f"\n   [{i+1}] ID: {doc_id}")
            print(f"       Title: {details['title'][:60]}...")
            print(f"       Embeddings: {details['embedding_count']} {has_emb}")
            print(f"       Created: {details['created_at']}")
            print(f"       Metadata: {'Has data' if details['metadata'] and details['metadata'] != {} else 'Empty {}'}")

    print()
    print("=" * 70)
    print()

    response = input("🤔 Proceed with fixing duplicates? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Aborted by user")
        return

    print()
    print("🚀 Processing duplicates...")
    print("-" * 70)

    fixed_count = 0
    deleted_count = 0

    for dup in duplicates:
        source_url = dup['source_url']
        ids = dup['ids']
        has_embeddings = dup['has_embeddings']

        print(f"\n📄 Processing: {source_url}")

        # Find the document with embeddings (keep this one)
        keeper_id = None
        delete_ids = []

        for i, doc_id in enumerate(ids):
            if has_embeddings[i] == 1:
                if keeper_id is None:
                    keeper_id = doc_id
                    print(f"   ✅ Keeping document {doc_id} (has embeddings)")
                else:
                    delete_ids.append(doc_id)
                    print(f"   ⚠️  Multiple docs with embeddings - will delete {doc_id}")
            else:
                delete_ids.append(doc_id)

        if keeper_id is None:
            # No document has embeddings - keep the oldest one
            keeper_id = ids[0]
            delete_ids = ids[1:]
            print(f"   ⚠️  No embeddings found - keeping oldest: {keeper_id}")

        # Transfer metadata from newest document (likely has updated metadata)
        source_id = ids[-1]  # Newest document

        if source_id != keeper_id:
            print(f"   📋 Transferring metadata from {source_id} to {keeper_id}")
            success = transfer_metadata(conn, source_id, keeper_id)

            if success:
                print(f"   ✅ Metadata transferred successfully")
                fixed_count += 1
            else:
                print(f"   ❌ Failed to transfer metadata")

        # Delete duplicates
        for delete_id in delete_ids:
            print(f"   🗑️  Deleting duplicate: {delete_id}")
            try:
                delete_document(conn, delete_id)
                deleted_count += 1
                print(f"   ✅ Deleted successfully")
            except Exception as e:
                print(f"   ❌ Failed to delete: {e}")

    print()
    print("=" * 70)
    print("📊 Summary")
    print("=" * 70)
    print(f"✅ Metadata transfers: {fixed_count}")
    print(f"🗑️  Documents deleted: {deleted_count}")
    print()
    print("🎉 Duplicate fixing complete!")
    print()
    print("💡 Next steps:")
    print("   1. Run the embeddings check SQL again to verify")
    print("   2. Test hybrid retrieval - should now work with proper metadata")
    print("   3. Process remaining documents without embeddings")

    conn.close()


if __name__ == '__main__':
    main()
