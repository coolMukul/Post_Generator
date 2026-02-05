"""
Migration Script: Fix arXiv Documents with Missing Metadata

This script finds arXiv documents with poor quality data and fetches
proper metadata from the arXiv API.

Issues Fixed:
- Title is URL or paper ID → Fetch real title from arXiv API
- Empty metadata {} → Populate with paper info (authors, abstract, etc.)

Usage:
    python scripts/fix_arxiv_metadata.py
"""

import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

# Load environment variables
load_dotenv()

# Database connection
DB_URL = os.getenv('DATABASE_URL')
if not DB_URL:
    print("❌ ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)


def fetch_arxiv_metadata(paper_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch metadata from arXiv API.

    Args:
        paper_id: arXiv paper ID (e.g., "2601.22151")

    Returns:
        Metadata dictionary or None if not found
    """
    api_url = f'http://export.arxiv.org/api/query?id_list={paper_id}'

    try:
        print(f"   📡 Fetching metadata for arXiv:{paper_id}")
        with urllib.request.urlopen(api_url, timeout=10) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)

        # Namespace for arXiv API
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entry = root.find('atom:entry', ns)

        if entry is None:
            print(f"   ⚠️  No entry found for arXiv:{paper_id}")
            return None

        # Extract metadata
        title_elem = entry.find('atom:title', ns)
        summary_elem = entry.find('atom:summary', ns)
        published_elem = entry.find('atom:published', ns)
        updated_elem = entry.find('atom:updated', ns)

        title = title_elem.text.strip().replace('\n', ' ') if title_elem is not None else None
        summary = summary_elem.text.strip() if summary_elem is not None else None
        published = published_elem.text if published_elem is not None else None
        updated = updated_elem.text if updated_elem is not None else None

        # Extract authors
        authors = []
        for author in entry.findall('atom:author', ns):
            name_elem = author.find('atom:name', ns)
            if name_elem is not None:
                authors.append(name_elem.text)

        # Extract categories
        categories = []
        for category in entry.findall('atom:category', ns):
            term = category.get('term')
            if term:
                categories.append(term)

        # Extract primary category
        primary_category = entry.find('arxiv:primary_category', {'arxiv': 'http://arxiv.org/schemas/atom'})
        primary_cat = primary_category.get('term') if primary_category is not None else None

        metadata = {
            'title': title,
            'authors': authors,
            'abstract': summary,
            'published_date': published,
            'updated_date': updated,
            'categories': categories,
            'primary_category': primary_cat,
            'source': 'arxiv',
            'arxiv_id': paper_id
        }

        print(f"   ✅ Found: {title[:60]}...")
        return metadata

    except urllib.error.URLError as e:
        print(f"   ❌ Network error: {e}")
        return None
    except ET.ParseError as e:
        print(f"   ❌ XML parsing error: {e}")
        return None
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return None


def extract_arxiv_id(url: str) -> Optional[str]:
    """
    Extract arXiv paper ID from URL.

    Examples:
        https://arxiv.org/pdf/2601.22151.pdf → 2601.22151
        https://arxiv.org/abs/2601.22151 → 2601.22151
        2601.22151 → 2601.22151
    """
    # Try various patterns
    patterns = [
        r'arxiv\.org/pdf/(\d+\.\d+)',  # PDF URL
        r'arxiv\.org/abs/(\d+\.\d+)',  # Abstract URL
        r'^(\d{4}\.\d{4,5})$',         # Just the ID
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def find_documents_needing_fix(conn) -> List[Dict[str, Any]]:
    """
    Find documents that need metadata fixing.

    Criteria:
    - URL contains arxiv.org
    - AND (title is NULL OR title is URL OR title is just paper ID OR metadata is empty)
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT id, url, title, source_url, metadata, created_at
            FROM documents
            WHERE (url LIKE '%arxiv.org%' OR source_url LIKE '%arxiv.org%')
              AND (
                  title IS NULL
                  OR title LIKE 'http%'
                  OR title ~ '^\\d+\\.\\d+$'
                  OR metadata = '{}'::jsonb
                  OR metadata IS NULL
              )
            ORDER BY created_at DESC
        """)

        documents = cur.fetchall()
        return [dict(doc) for doc in documents]


def update_document(conn, doc_id: str, title: str, metadata: Dict[str, Any]) -> bool:
    """
    Update document with fetched metadata.

    Returns:
        True if successful, False otherwise
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE documents
                SET title = %s, metadata = %s
                WHERE id = %s
            """, (title, metadata, doc_id))

        conn.commit()
        return True

    except Exception as e:
        print(f"   ❌ Database update error: {e}")
        conn.rollback()
        return False


def main():
    """Main migration script."""
    print("=" * 70)
    print("🔧 arXiv Metadata Migration Script")
    print("=" * 70)
    print()

    # Connect to database
    print("📊 Connecting to database...")
    try:
        conn = psycopg.connect(DB_URL)
        print("✅ Connected successfully")
        print()
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

    # Find documents needing fix
    print("🔍 Searching for documents needing metadata fix...")
    documents = find_documents_needing_fix(conn)
    print(f"✅ Found {len(documents)} documents to fix")
    print()

    if not documents:
        print("🎉 No documents need fixing! All good.")
        return

    # Show preview
    print("📋 Preview of documents to fix:")
    print("-" * 70)
    for i, doc in enumerate(documents[:5], 1):
        print(f"{i}. ID: {doc['id']}")
        print(f"   URL: {doc['url'] or doc['source_url']}")
        print(f"   Current Title: {doc['title'] or '(None)'}")
        print(f"   Metadata: {'Empty {}' if not doc['metadata'] or doc['metadata'] == {} else 'Has data'}")
        print()

    if len(documents) > 5:
        print(f"   ... and {len(documents) - 5} more")
        print()

    # Ask for confirmation
    response = input("🤔 Proceed with fixing these documents? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Aborted by user")
        return

    print()
    print("🚀 Starting migration...")
    print("-" * 70)

    # Process each document
    success_count = 0
    failed_count = 0
    skipped_count = 0

    for i, doc in enumerate(documents, 1):
        print(f"\n[{i}/{len(documents)}] Processing document {doc['id'][:8]}...")

        # Extract arXiv ID
        url = doc['url'] or doc['source_url'] or ''
        title = doc['title'] or ''

        # Try to get arXiv ID from URL or title
        arxiv_id = extract_arxiv_id(url) or extract_arxiv_id(title)

        if not arxiv_id:
            print(f"   ⚠️  Could not extract arXiv ID from URL or title")
            skipped_count += 1
            continue

        # Fetch metadata from arXiv API
        metadata = fetch_arxiv_metadata(arxiv_id)

        if not metadata or not metadata.get('title'):
            print(f"   ⚠️  Failed to fetch metadata from arXiv API")
            failed_count += 1
            continue

        # Update database
        new_title = metadata['title']
        success = update_document(conn, doc['id'], new_title, metadata)

        if success:
            print(f"   ✅ Updated: {new_title[:60]}...")
            success_count += 1
        else:
            failed_count += 1

        # Be nice to arXiv API - rate limiting
        if i < len(documents):
            time.sleep(1)  # 1 second delay between requests

    # Summary
    print()
    print("=" * 70)
    print("📊 Migration Summary")
    print("=" * 70)
    print(f"✅ Successfully updated: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"⚠️  Skipped: {skipped_count}")
    print(f"📝 Total processed: {len(documents)}")
    print()

    if success_count > 0:
        print("🎉 Migration completed successfully!")
        print()
        print("💡 Next steps:")
        print("   1. Check the documents table to verify updates")
        print("   2. Test hybrid retrieval to see improved search results")
        print("   3. Consider implementing full Phase 2 PDF processing")
    else:
        print("⚠️  No documents were updated. Check the errors above.")

    # Close connection
    conn.close()


if __name__ == '__main__':
    main()
