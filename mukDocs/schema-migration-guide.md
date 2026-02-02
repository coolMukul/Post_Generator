# Schema Migration Guide

## Overview

The database schema has been updated to support a multi-project, reusable document ingestion system. This document outlines what has been changed and what still needs to be updated.

## Completed Changes

### ✅ Database Schema (`scripts/init_db.sql`)
- Migrated from SERIAL integer IDs to UUID primary keys
- Added `projects` table for multi-tenancy
- Added `project_documents` table for many-to-many relationships
- Renamed `vectors` to `document_vectors` with `project_document_id` FK
- Enhanced `documents` table with:
  - `file_type`, `file_size`, `blob_reference`
  - Parsing tracking: `parsing_attempts`, `parsing_failures`, `last_parsing_error`
  - `parsing_blocked` flag
- Seeded with `researchpaper` project

### ✅ API TypeScript Schemas (`packages/api/src/types/schemas.ts`)
- Updated all schemas to use UUID strings
- Added `Project` and `ProjectDocument` schemas
- Added `ProjectDocumentStatus` enum
- Updated `ProcessPdfRequest` to include optional `project_key`
- Updated `QueryRequest` to filter by `project_key`

### ✅ UI Environment Configuration
- Updated `packages/ui/app/ingest/page.tsx` to use `NEXT_PUBLIC_API_URL`
- Created `packages/ui/.env` with API URL configuration

## Required Changes (TODO)

### 🔄 Python Worker Repositories

#### 1. `packages/workers/src/repositories/document_repository.py`

**Current Structure:**
```python
create_document(url, title, metadata) -> Dict
- Uses integer IDs
- Direct document creation
- Checksum-based deduplication
```

**Required Structure:**
```python
create_document(title, source_url, file_type, file_size, blob_reference, checksum, metadata) -> str (UUID)
- Returns UUID string
- More comprehensive document fields
- Support parsing tracking fields

link_document_to_project(document_id: str, project_key: str) -> str (project_document_id)
- Creates project_documents entry
- Returns project_document UUID

get_project_by_key(project_key: str) -> Dict
- Fetches project by key

update_parsing_status(document_id: str, success: bool, error: str = None)
- Increments parsing_attempts
- Updates parsing_failures if failed
- Sets last_parsing_error and last_parsing_attempt_at
```

#### 2. `packages/workers/src/repositories/vector_repository.py`

**Current Structure:**
```python
store_vector(document_id: int, chunk_index, content, context_summary, embedding, token_count)
- Uses document_id (integer)
- Inserts into vectors table
```

**Required Structure:**
```python
store_vector(project_document_id: str, chunk_index, content, context_summary, embedding, token_count, metadata)
- Uses project_document_id (UUID)
- Inserts into document_vectors table
- Supports chunk-level metadata

search_similar(embedding, limit, project_key, document_id=None)
- Filters by project via JOIN on project_documents
- Optional document filter
- Returns results with document title
```

#### 3. `packages/workers/src/jobs/pdf_processor.py`

**Current Structure:**
```python
process_pdf(url, title, metadata) -> Dict
- Creates document directly
- Stores vectors with document_id
```

**Required Structure:**
```python
process_pdf(url, title, project_key, metadata) -> Dict
- Get project_id from project_key
- Create document (returns document_id UUID)
- Link document to project (returns project_document_id UUID)
- Update project_documents status to 'processing'
- Process PDF and create chunks
- Store vectors with project_document_id
- Update project_documents status to 'completed'/'failed'
- Track parsing attempts/failures
```

### 🔄 API Handlers

#### `packages/api/src/handlers/pdf.handler.ts`

Update to pass `project_key` to the worker job:
```typescript
export async function submitPdfProcessingJob(data: ProcessPdfRequest) {
  const jobData: ProcessPdfJobData = {
    url: data.url,
    title: data.title,
    project_key: data.project_key || 'researchpaper',
    metadata: data.metadata
  };
  // ... rest of job submission
}
```

#### `packages/api/src/handlers/query.handler.ts`

Update to filter by `project_key` and handle UUID document IDs:
```typescript
export async function queryVectors(params: QueryRequest) {
  // Query should filter by project_key
  // Document IDs should be UUID strings
}
```

## Database Migration Steps

If you have existing data:

1. **Backup your database:**
   ```powershell
   pg_dump -U postgenerator post_generator > backup.sql
   ```

2. **Drop and recreate (for development):**
   ```powershell
   psql -U postgres
   ```
   ```sql
   DROP DATABASE post_generator;
   CREATE DATABASE post_generator;
   \c post_generator
   CREATE EXTENSION vector;
   \i scripts/init_db.sql
   ```

3. **Or migrate existing data (production):**
   - Create new tables with different names
   - Migrate data with UUID generation
   - Drop old tables
   - Rename new tables

## Testing the Updated System

### 1. Start Services (PowerShell)

**Terminal 1 - PostgreSQL:**
```powershell
# Make sure PostgreSQL is running
pg_ctl -D "C:\Program Files\PostgreSQL\15\data" status
```

**Terminal 2 - Redis:**
```powershell
redis-server
```

**Terminal 3 - API:**
```powershell
cd packages/api
pnpm dev
```

**Terminal 4 - Worker:**
```powershell
cd packages/workers
.\.venv\Scripts\activate  # or source venv/bin/activate on Git Bash
python -m src.worker
```

**Terminal 5 - UI:**
```powershell
cd packages/ui
pnpm dev
```

### 2. Test Endpoints

**Submit PDF:**
```powershell
curl -X POST http://localhost:3201/pdf/process `
  -H "Content-Type: application/json" `
  -d '{\"url\":\"https://arxiv.org/pdf/2301.00001.pdf\",\"title\":\"Test Paper\",\"project_key\":\"researchpaper\"}'
```

**Check Job Status:**
```powershell
curl http://localhost:3201/jobs/JOB_ID_HERE
```

**Query Vectors:**
```powershell
curl -X POST http://localhost:3201/query `
  -H "Content-Type: application/json" `
  -d '{\"query\":\"machine learning\",\"limit\":5,\"project_key\":\"researchpaper\"}'
```

### 3. Verify in Database

```sql
-- Check projects
SELECT * FROM projects;

-- Check documents
SELECT id, title, source_url, created_at FROM documents;

-- Check project-document linkage
SELECT
  pd.id,
  p.key as project,
  d.title,
  pd.status
FROM project_documents pd
JOIN projects p ON pd.project_id = p.id
JOIN documents d ON pd.document_id = d.id;

-- Check vectors
SELECT
  COUNT(*) as vector_count,
  pd.id as project_doc_id,
  d.title
FROM document_vectors dv
JOIN project_documents pd ON dv.project_document_id = pd.id
JOIN documents d ON pd.document_id = d.id
GROUP BY pd.id, d.title;
```

## Environment Variables

Make sure your `.env` file includes:

```bash
# Database
DATABASE_URL=postgresql://postgenerator:your_password@localhost:5432/post_generator

# API
API_PORT=3201

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# OpenAI
OPENAI_API_KEY=sk-...

# LlamaParse
LLAMA_CLOUD_API_KEY=llx-...
```

And `packages/ui/.env`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:3201
```

## Next Steps

1. Update Python worker repositories as outlined above
2. Update API handlers to use new schema
3. Test end-to-end PDF processing
4. Test vector search with project filtering
5. Verify multi-project support by creating additional projects
