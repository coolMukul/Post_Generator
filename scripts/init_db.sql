-- Research Insight Database Schema
-- Multi-project reusable document ingestion system

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Generic documents table (reusable across future projects)
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  source_url TEXT,
  file_type TEXT, -- 'pdf', 'docx', 'txt', etc.
  file_size BIGINT,
  blob_reference TEXT, -- Azure Blob or local storage path
  checksum TEXT, -- For deduplication
  metadata JSONB DEFAULT '{}'::jsonb, -- Flexible: authors, abstract, etc.
  parsing_attempts INTEGER DEFAULT 0, -- Number of parsing attempts
  parsing_failures INTEGER DEFAULT 0, -- Number of parsing failures
  last_parsing_error TEXT, -- Last parsing error message
  last_parsing_attempt_at TIMESTAMP, -- When last parsing was attempted
  parsing_blocked BOOLEAN DEFAULT FALSE, -- Block further parsing attempts
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Projects/use-cases table (enables multi-tenancy)
CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key TEXT UNIQUE NOT NULL, -- 'researchpaper', 'legal-analysis', 'product-docs', etc.
  name TEXT NOT NULL,
  description TEXT,
  settings JSONB DEFAULT '{}'::jsonb, -- Project-specific configs
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Many-to-many: Documents can belong to multiple projects
CREATE TABLE IF NOT EXISTS project_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
  project_metadata JSONB DEFAULT '{}'::jsonb, -- Project-specific metadata
  error_message TEXT,
  added_at TIMESTAMP DEFAULT NOW(),
  processed_at TIMESTAMP,
  UNIQUE(project_id, document_id)
);

-- Vector embeddings (isolated per project via project_documents)
-- NOTE: Vector dimension should match EMBEDDING_DIMENSION in .env
-- Change vector(1536) to match your embedding model's dimension:
--   - OpenAI text-embedding-3-small: 1536
--   - OpenAI text-embedding-3-large: 3072
--   - Voyage AI voyage-3-large: 1024
--   - Cohere embed-english-v3.0: 1024
CREATE TABLE IF NOT EXISTS document_vectors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_document_id UUID REFERENCES project_documents(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL, -- Order of chunks in document
  content TEXT NOT NULL,
  context_summary TEXT, -- GPT-4 generated contextual summary
  embedding vector(1536), -- Must match EMBEDDING_DIMENSION env var
  token_count INTEGER,
  metadata JSONB DEFAULT '{}'::jsonb, -- Chunk-level metadata
  created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_checksum ON documents(checksum);
CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_parsing_blocked ON documents(parsing_blocked) WHERE parsing_blocked = TRUE;
CREATE INDEX IF NOT EXISTS idx_projects_key ON projects(key);
CREATE INDEX IF NOT EXISTS idx_project_documents_project ON project_documents(project_id);
CREATE INDEX IF NOT EXISTS idx_project_documents_document ON project_documents(document_id);
CREATE INDEX IF NOT EXISTS idx_project_documents_status ON project_documents(project_id, status);
CREATE INDEX IF NOT EXISTS idx_document_vectors_project_doc ON document_vectors(project_document_id);
CREATE INDEX IF NOT EXISTS idx_document_vectors_chunk ON document_vectors(project_document_id, chunk_index);

-- Vector similarity search index (adjust lists based on data size)
CREATE INDEX IF NOT EXISTS idx_document_vectors_embedding ON document_vectors
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Initial project seed
INSERT INTO projects (key, name, description, settings)
VALUES (
  'researchpaper',
  'Research Paper Analysis',
  'LinkedIn content generation from academic papers',
  '{"embedding_model": "text-embedding-3-small", "chunk_size": 1500, "chunk_overlap": 200}'::jsonb
)
ON CONFLICT (key) DO NOTHING;

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to documents
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to projects
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Verify tables were created
SELECT
    tablename,
    schemaname
FROM pg_tables
WHERE schemaname = 'public'
    AND tablename IN ('documents', 'projects', 'project_documents', 'document_vectors');

-- Verify pgvector extension is installed
SELECT
    extname,
    extversion
FROM pg_extension
WHERE extname = 'vector';

-- Display table structures
\d documents
\d projects
\d project_documents
\d document_vectors
