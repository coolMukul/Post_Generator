-- Initialize database schema for Post Generator
-- Run this script after creating the database and enabling pgvector extension

-- Enable pgvector extension (must be run as superuser)
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table
-- Stores metadata about processed documents
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT,
    checksum VARCHAR(64) UNIQUE NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for documents table
CREATE INDEX IF NOT EXISTS idx_documents_checksum ON documents(checksum);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_url ON documents(url);

-- Vectors table
-- Stores document chunks with their embeddings
CREATE TABLE IF NOT EXISTS vectors (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    context_summary TEXT,
    embedding VECTOR(1536),  -- OpenAI text-embedding-3-small dimensions
    token_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for vectors table
CREATE INDEX IF NOT EXISTS idx_vectors_document_id ON vectors(document_id);
CREATE INDEX IF NOT EXISTS idx_vectors_chunk_index ON vectors(document_id, chunk_index);

-- Vector similarity search index (IVFFlat)
-- Note: This index requires data to be present for optimal performance
-- Consider creating this after initial data load
CREATE INDEX IF NOT EXISTS idx_vectors_embedding ON vectors
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Alternative: Use HNSW index (requires pgvector 0.5.0+)
-- CREATE INDEX IF NOT EXISTS idx_vectors_embedding_hnsw ON vectors
-- USING hnsw (embedding vector_cosine_ops);

-- Verify tables were created
SELECT
    tablename,
    schemaname
FROM pg_tables
WHERE schemaname = 'public'
    AND tablename IN ('documents', 'vectors');

-- Verify pgvector extension is installed
SELECT
    extname,
    extversion
FROM pg_extension
WHERE extname = 'vector';

-- Display table structures
\d documents
\d vectors
