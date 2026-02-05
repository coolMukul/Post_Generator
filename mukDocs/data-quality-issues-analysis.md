# Data Quality Issues Analysis & Solutions

## 🔍 Problem Summary

Based on database investigation, there are critical data quality issues affecting hybrid retrieval:

### Issues Identified:

1. **Title Field** - Inconsistent values:
   - ✅ Row 1, 6: Proper titles ("Late Breaking Results...", "From Logits to Latents...")
   - ❌ Rows 2-4: Just paper IDs ("2601.22151", "2601.22028")
   - ❌ Row 5: Full URL ("https://arxiv.org/pdf/2602.02230")

2. **blob_reference Field** - NULL for most documents:
   - Should contain: Local file path (e.g., "downloads\arxiv-2601.22151.pdf")
   - Currently: `[null]` for 5 out of 6 documents

3. **metadata Field** - Empty JSON `{}`:
   - Should contain: Document metadata (title, authors, abstract, etc.)
   - Currently: Only rows 1 and 6 have partial metadata with title

### Impact on Search:

- ❌ Hybrid retrieval can't properly rank results (missing title context)
- ❌ Search UI shows poor document titles (URLs instead of real titles)
- ❌ Keyword search has limited context (empty metadata)
- ❌ Can't access original PDF files (no blob_reference)

---

## 🔎 Root Cause Analysis

### Data Flow:

```
UI (ingest page)
  → API (pdf.handler.ts)
  → BullMQ Queue
  → Worker (pdf_processor.py)
  → DocumentRepository
  → Database
```

### Issue at Each Stage:

#### 1. **UI Stage** (`packages/ui/app/ingest/page.tsx`)

**Current Implementation:**
```typescript
// Line 75-78
body: JSON.stringify({
  url,
  title: title || undefined,  // ← Only sends URL and optional title
})
```

**Problem:**
- Title field is optional - users often leave it blank
- No metadata extraction at UI level
- No validation of URL format

---

#### 2. **API Stage** (`packages/api/src/handlers/pdf.handler.ts`)

**Current Implementation:**
```typescript
// Lines 4-15
export const submitPdfProcessingJob = async (data: ProcessPdfJobData): Promise<JobResponse> => {
  const job = await mainProcessingQueue.add('process-pdf', data, {
    jobId: `pdf-${Date.now()}-${Math.random().toString(36).substring(7)}`,
  });
  // Just passes data through to queue
}
```

**Problem:**
- No title extraction from URL (e.g., arxiv paper ID → title lookup)
- No metadata enrichment
- Just passes data through unchanged

---

#### 3. **Worker Stage** (`packages/workers/src/jobs/pdf_processor.py`)

**Current Implementation (Phase 1 Stub):**
```python
# Lines 30-43
url = job_data.get('url')
title = job_data.get('title')  # ← May be None
metadata = job_data.get('metadata', {})  # ← Usually empty {}

# Initialize repositories
db_url = get_database_url()
doc_repo = DocumentRepository(db_url)

# Phase 1: Create document entry (stub)
document = doc_repo.create_document(url=url, title=title, metadata=metadata)
# ← Passes None/empty values directly to database

# TODO Phase 2: Implement the following:
# 1. Download PDF from URL
# 2. Parse PDF using LlamaParse
# 3. Split text into chunks
# 4. Generate embeddings using OpenAI
# 5. Store vectors in database
# 6. Update document metadata with processing stats
```

**Problem:**
- ❌ No PDF download → blob_reference stays NULL
- ❌ No metadata extraction → metadata stays {}
- ❌ No title extraction → title may be None/URL
- ❌ Phase 1 stub never implemented Phase 2 features

---

#### 4. **Repository Stage** (`packages/workers/src/repositories/document_repository.py`)

**Current Implementation:**
```python
# Lines 50-57
cur.execute(
    """
    INSERT INTO documents (url, title, checksum, metadata, created_at)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING *
    """,
    (url, title, checksum, metadata or {}, datetime.now())
)
# ← Inserts whatever values are passed in (including None/empty)
```

**Problem:**
- No validation or defaults
- Accepts NULL title, empty metadata
- No blob_reference handling

---

## 💡 Solution: Enhanced PDF Processing Pipeline

### Phase 2+ Implementation Requirements:

The PDF processor needs to be enhanced with the following stages:

---

### **Stage 1: Pre-Processing - URL Analysis & Title Extraction**

Before downloading, extract metadata from URL when possible:

```python
def extract_metadata_from_url(url: str) -> Dict[str, Any]:
    """
    Extract metadata from URL patterns.

    Supported sources:
    - arXiv: https://arxiv.org/pdf/2601.22151.pdf → Query arXiv API
    - DOI: https://doi.org/10.1234/example → Query CrossRef API
    - Other: Use URL as fallback
    """
    metadata = {}

    # arXiv detection
    arxiv_match = re.match(r'https://arxiv\.org/pdf/(\d+\.\d+)', url)
    if arxiv_match:
        paper_id = arxiv_match.group(1)
        metadata = fetch_arxiv_metadata(paper_id)  # API call
        # Returns: {title, authors, abstract, published_date, categories}

    # DOI detection
    doi_match = re.search(r'10\.\d{4,}/[\w\-.]+', url)
    if doi_match:
        doi = doi_match.group(0)
        metadata = fetch_crossref_metadata(doi)  # API call

    return metadata

def fetch_arxiv_metadata(paper_id: str) -> Dict[str, Any]:
    """Fetch metadata from arXiv API."""
    import urllib.request
    import xml.etree.ElementTree as ET

    api_url = f'http://export.arxiv.org/api/query?id_list={paper_id}'
    with urllib.request.urlopen(api_url) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    entry = root.find('{http://www.w3.org/2005/Atom}entry')

    if entry:
        title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
        summary = entry.find('{http://www.w3.org/2005/Atom}summary').text.strip()
        authors = [
            author.find('{http://www.w3.org/2005/Atom}name').text
            for author in entry.findall('{http://www.w3.org/2005/Atom}author')
        ]
        published = entry.find('{http://www.w3.org/2005/Atom}published').text

        return {
            'title': title,
            'authors': authors,
            'abstract': summary,
            'published_date': published,
            'source': 'arxiv',
            'paper_id': paper_id
        }

    return {}
```

**Benefits:**
- ✅ Get proper title before download
- ✅ Get authors, abstract, publication info
- ✅ No need for PDF parsing for metadata
- ✅ Works even if PDF download fails

---

### **Stage 2: Download - PDF File Retrieval**

Download PDF and save locally:

```python
def download_pdf(url: str, output_dir: str = 'downloads') -> str:
    """
    Download PDF from URL and save locally.

    Args:
        url: PDF URL
        output_dir: Directory to save PDFs

    Returns:
        Local file path (blob_reference)
    """
    import urllib.request
    import os

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Generate filename from URL
    filename = url.split('/')[-1]
    if not filename.endswith('.pdf'):
        # Extract paper ID for better naming
        arxiv_match = re.match(r'https://arxiv\.org/pdf/(\d+\.\d+)', url)
        if arxiv_match:
            filename = f"arxiv-{arxiv_match.group(1)}.pdf"
        else:
            filename = f"document-{hashlib.md5(url.encode()).hexdigest()}.pdf"

    filepath = os.path.join(output_dir, filename)

    # Download file
    logger.info(f"Downloading PDF from {url} to {filepath}")
    urllib.request.urlretrieve(url, filepath)

    # Verify file
    if not os.path.exists(filepath):
        raise Exception(f"Failed to download PDF to {filepath}")

    file_size = os.path.getsize(filepath)
    logger.info(f"Downloaded PDF: {file_size} bytes")

    return filepath  # This becomes blob_reference
```

**Benefits:**
- ✅ PDF saved locally with blob_reference
- ✅ Can access original file later
- ✅ Smart filename generation
- ✅ File verification

---

### **Stage 3: Parsing - Extract Text & Metadata from PDF**

Parse PDF to extract content and metadata:

```python
def parse_pdf_with_llama(filepath: str) -> Dict[str, Any]:
    """
    Parse PDF using LlamaParse for text extraction.

    Args:
        filepath: Local PDF file path

    Returns:
        Parsed content with metadata
    """
    from llama_parse import LlamaParse

    parser = LlamaParse(
        api_key=os.getenv('LLAMA_CLOUD_API_KEY'),
        result_type='markdown',
        num_workers=4,
        verbose=True,
        language='en'
    )

    documents = parser.load_data(filepath)

    # Combine all pages
    full_text = '\n\n'.join([doc.text for doc in documents])

    # Extract metadata if not already present
    metadata = {}
    if documents and hasattr(documents[0], 'metadata'):
        metadata = documents[0].metadata

    return {
        'text': full_text,
        'pages': len(documents),
        'metadata': metadata
    }

def parse_pdf_fallback(filepath: str) -> Dict[str, Any]:
    """
    Fallback PDF parser using pypdf.

    Use when LlamaParse is unavailable or fails.
    """
    from pypdf import PdfReader

    reader = PdfReader(filepath)

    # Extract text from all pages
    full_text = ''
    for page in reader.pages:
        full_text += page.extract_text() + '\n\n'

    # Extract PDF metadata
    pdf_metadata = reader.metadata or {}
    metadata = {
        'title': pdf_metadata.get('/Title', ''),
        'author': pdf_metadata.get('/Author', ''),
        'subject': pdf_metadata.get('/Subject', ''),
        'creator': pdf_metadata.get('/Creator', ''),
    }

    return {
        'text': full_text,
        'pages': len(reader.pages),
        'metadata': {k: v for k, v in metadata.items() if v}
    }
```

**Benefits:**
- ✅ Extract full text content
- ✅ Get PDF metadata (title, author from PDF properties)
- ✅ Fallback parser for reliability
- ✅ Page count for statistics

---

### **Stage 4: Update - Save Complete Metadata**

Update document with all extracted information:

```python
def update_document_with_metadata(
    doc_repo: DocumentRepository,
    document_id: str,
    url_metadata: Dict[str, Any],
    pdf_metadata: Dict[str, Any],
    blob_reference: str,
    user_title: Optional[str]
) -> Dict[str, Any]:
    """
    Merge and save all metadata sources.

    Priority order for title:
    1. User-provided title (if exists)
    2. arXiv/DOI API title (if exists)
    3. PDF metadata title (if exists)
    4. Extract from URL as last resort
    """
    # Determine best title
    title = (
        user_title or
        url_metadata.get('title') or
        pdf_metadata.get('title') or
        extract_title_from_url(url)
    )

    # Merge metadata
    merged_metadata = {
        **pdf_metadata,  # Base layer
        **url_metadata,   # Overwrite with API data
        'file_size': os.path.getsize(blob_reference),
        'pages': pdf_metadata.get('pages', 0),
    }

    # Update document in database
    updated_doc = doc_repo.update_document_complete(
        document_id=document_id,
        title=title,
        blob_reference=blob_reference,
        metadata=merged_metadata
    )

    return updated_doc
```

---

### **Complete Enhanced PDF Processor:**

```python
async def process_pdf_job(job_id: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced PDF processing with complete metadata extraction."""
    logger.info(f"[Job {job_id}] Starting enhanced PDF processing")

    url = job_data.get('url')
    user_title = job_data.get('title')
    project_key = job_data.get('project_key', 'researchpaper')

    if not url:
        raise ValueError("URL is required")

    try:
        # Initialize repositories
        db_url = get_database_url()
        doc_repo = DocumentRepository(db_url)
        vector_repo = VectorRepository(db_url)

        # STAGE 1: Extract metadata from URL (arXiv, DOI, etc.)
        logger.info(f"[Job {job_id}] Stage 1: Extracting metadata from URL")
        url_metadata = extract_metadata_from_url(url)

        # Use URL metadata title if no user title provided
        initial_title = user_title or url_metadata.get('title') or extract_title_from_url(url)

        # Create document entry with initial data
        logger.info(f"[Job {job_id}] Creating document entry: {initial_title}")
        document = doc_repo.create_document(
            url=url,
            title=initial_title,
            metadata=url_metadata
        )
        document_id = document['id']

        # STAGE 2: Download PDF
        logger.info(f"[Job {job_id}] Stage 2: Downloading PDF")
        blob_reference = download_pdf(url, output_dir='downloads')

        # STAGE 3: Parse PDF
        logger.info(f"[Job {job_id}] Stage 3: Parsing PDF")
        try:
            parsed_data = parse_pdf_with_llama(blob_reference)
        except Exception as e:
            logger.warning(f"[Job {job_id}] LlamaParse failed: {e}, using fallback")
            parsed_data = parse_pdf_fallback(blob_reference)

        full_text = parsed_data['text']
        pdf_metadata = parsed_data['metadata']

        # STAGE 4: Update document with complete metadata
        logger.info(f"[Job {job_id}] Stage 4: Updating document metadata")
        final_doc = update_document_with_metadata(
            doc_repo=doc_repo,
            document_id=document_id,
            url_metadata=url_metadata,
            pdf_metadata=pdf_metadata,
            blob_reference=blob_reference,
            user_title=user_title
        )

        # STAGE 5: Chunk text
        logger.info(f"[Job {job_id}] Stage 5: Chunking text")
        chunks = chunk_text(full_text, chunk_size=1000, overlap=200)

        # STAGE 6: Generate embeddings and store vectors
        logger.info(f"[Job {job_id}] Stage 6: Generating embeddings")
        embeddings = generate_embeddings_batch(chunks)  # OpenAI API call

        logger.info(f"[Job {job_id}] Stage 7: Storing vectors")
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_repo.create_vector(
                document_id=document_id,
                chunk_index=idx,
                content=chunk,
                embedding=embedding,
                metadata={'chunk_size': len(chunk)}
            )

        logger.info(f"[Job {job_id}] Processing complete")
        return {
            "document_id": document_id,
            "url": url,
            "title": final_doc['title'],
            "blob_reference": blob_reference,
            "status": "completed",
            "chunks_processed": len(chunks),
            "vectors_created": len(embeddings),
            "pages": parsed_data.get('pages', 0),
            "metadata": final_doc['metadata']
        }

    except Exception as e:
        logger.error(f"[Job {job_id}] Processing failed: {str(e)}", exc_info=True)
        raise
```

---

## 📋 Implementation Checklist

### Phase 2: Enhanced PDF Processing

- [ ] **URL Metadata Extraction**
  - [ ] Implement arXiv API integration
  - [ ] Implement DOI/CrossRef API integration
  - [ ] Add URL pattern detection
  - [ ] Handle API rate limiting

- [ ] **PDF Download**
  - [ ] Implement download function with retry logic
  - [ ] Create downloads directory structure
  - [ ] Add file verification
  - [ ] Handle download errors gracefully

- [ ] **PDF Parsing**
  - [ ] Integrate LlamaParse
  - [ ] Implement pypdf fallback
  - [ ] Extract text content
  - [ ] Extract PDF metadata

- [ ] **Document Repository Updates**
  - [ ] Add `update_document_complete()` method
  - [ ] Support blob_reference updates
  - [ ] Support metadata merging
  - [ ] Add title update capability

- [ ] **Metadata Merging**
  - [ ] Implement priority logic (user > API > PDF > URL)
  - [ ] Merge metadata from multiple sources
  - [ ] Validate required fields
  - [ ] Handle missing data gracefully

- [ ] **Text Chunking**
  - [ ] Implement chunking with overlap
  - [ ] Add context preservation
  - [ ] Generate chunk metadata

- [ ] **Embedding Generation**
  - [ ] Integrate OpenAI embeddings API
  - [ ] Add batch processing
  - [ ] Handle API errors and retries
  - [ ] Cache embeddings

- [ ] **Vector Storage**
  - [ ] Link vectors to documents properly
  - [ ] Store embeddings efficiently
  - [ ] Add vector metadata

---

## 🔧 Quick Fix for Existing Data

While implementing full Phase 2, you can partially fix existing data:

### Option 1: Retroactive Metadata Extraction (Recommended)

For documents with URLs but missing metadata:

```sql
-- Find documents with empty titles or metadata
SELECT id, url, title, metadata
FROM documents
WHERE title IS NULL
   OR title LIKE 'http%'
   OR title ~ '^\d+\.\d+$'  -- arXiv IDs
   OR metadata = '{}'::jsonb;
```

Then run a migration script:
```python
# migration_script.py
def fix_arxiv_documents():
    """Fix arXiv documents with missing metadata."""
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor(row_factory=dict_row)

    # Find arxiv documents
    cur.execute("""
        SELECT id, url, title, metadata
        FROM documents
        WHERE url LIKE '%arxiv.org%'
          AND (title IS NULL OR title LIKE 'http%' OR title ~ '^\\d+\\.\\d+$' OR metadata = '{}'::jsonb)
    """)

    documents = cur.fetchall()
    print(f"Found {len(documents)} documents to fix")

    for doc in documents:
        # Extract arXiv ID
        match = re.search(r'(\d+\.\d+)', doc['url'])
        if match:
            paper_id = match.group(1)

            # Fetch metadata from arXiv API
            metadata = fetch_arxiv_metadata(paper_id)

            if metadata:
                # Update database
                cur.execute("""
                    UPDATE documents
                    SET title = %s, metadata = %s
                    WHERE id = %s
                """, (metadata['title'], metadata, doc['id']))

                print(f"✅ Updated document {doc['id']}: {metadata['title'][:50]}")

    conn.commit()
```

### Option 2: Manual Data Cleanup

Update specific documents via SQL:

```sql
-- Fix specific document titles
UPDATE documents
SET title = 'Late Breaking Results: Conversion of Neural Networks into Logic Flows for Edge Computing'
WHERE id = '11bf112b-fd9c-4902-afa4-9957ae48ae0e';

UPDATE documents
SET title = 'Proper Title Here'
WHERE title = '2601.22151';
```

---

## 🎯 Priority Actions

### Immediate (This Week):
1. ✅ **Run migration script** to fix existing arXiv documents
2. ✅ **Implement Stage 1** (URL metadata extraction) - Quickest impact
3. ✅ **Implement Stage 2** (PDF download) - Needed for blob_reference

### Short Term (Next 2 Weeks):
4. ✅ **Implement Stage 3** (PDF parsing)
5. ✅ **Update document repository** with new methods
6. ✅ **Test complete pipeline** with real documents

### Medium Term (Future):
7. ✅ **Add more source APIs** (DOI, PubMed, etc.)
8. ✅ **Implement caching** for API calls
9. ✅ **Add error recovery** and retry logic
10. ✅ **Monitor data quality** with automated checks

---

## 📊 Success Metrics

After implementing fixes, verify:

- ✅ **0% documents with NULL titles** (excluding intentional cases)
- ✅ **0% documents with URL as title**
- ✅ **100% documents with blob_reference** (for successfully downloaded PDFs)
- ✅ **100% documents with metadata** (at minimum: title, source)
- ✅ **Improved search quality** - Users find relevant results
- ✅ **Better UI display** - Proper titles shown in search results

---

## 🤔 Questions to Consider

1. **Storage**: Where should PDFs be stored long-term?
   - Local filesystem: `downloads/` directory
   - Cloud storage: S3, Azure Blob, Google Cloud Storage
   - Hybrid: Local cache + cloud backup

2. **API Keys**: Which services need API keys?
   - ✅ arXiv: No API key needed (public API)
   - ❓ CrossRef: Optional API key (better rate limits)
   - ✅ LlamaParse: Requires `LLAMA_CLOUD_API_KEY`
   - ✅ OpenAI: Requires `OPENAI_API_KEY`

3. **Error Handling**: What if metadata extraction fails?
   - Fallback to basic URL-based title
   - Mark document for manual review
   - Retry with different parser

4. **Existing Documents**: How to handle documents already in DB?
   - Run migration script (recommended)
   - OR: Reprocess all documents
   - OR: Fix on-demand when accessed

---

## 💬 Recommendation

**Prioritize implementing Stages 1-4** (URL metadata → Download → Parse → Update) before moving to Phase 4. Phase 3 (hybrid retrieval) is technically complete, but **data quality blocks its effectiveness**.

Once documents have proper titles, metadata, and blob_references:
- ✅ Hybrid retrieval will work much better
- ✅ Search results will be more relevant
- ✅ UI will display proper information
- ✅ Users can access original PDFs

This is **blocking Phase 3 testing** and should be **higher priority than Phase 4** until resolved!
