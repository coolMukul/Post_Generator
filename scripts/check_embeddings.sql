-- Check Embeddings Status for Documents
-- Run this to verify if embeddings were properly saved for your documents

-- ====================================================================
-- 1. Count documents vs embeddings
-- ====================================================================
SELECT
    'Total Documents' as metric,
    COUNT(*) as count
FROM documents
UNION ALL
SELECT
    'Documents with Embeddings',
    COUNT(DISTINCT pd.document_id)
FROM project_documents pd
JOIN document_vectors dv ON dv.project_document_id = pd.id
UNION ALL
SELECT
    'Total Embedding Vectors',
    COUNT(*)
FROM document_vectors;

-- ====================================================================
-- 2. Check specific documents by source URL
-- ====================================================================
SELECT
    d.id,
    d.title,
    d.source_url,
    COUNT(dv.id) as embedding_count,
    CASE
        WHEN COUNT(dv.id) > 0 THEN 'YES ✅'
        ELSE 'NO ❌'
    END as has_embeddings
FROM documents d
LEFT JOIN project_documents pd ON pd.document_id = d.id
LEFT JOIN document_vectors dv ON dv.project_document_id = pd.id
WHERE d.source_url LIKE '%arxiv.org%'
GROUP BY d.id, d.title, d.source_url
ORDER BY d.created_at DESC;

-- ====================================================================
-- 3. Detailed embedding info for each document
-- ====================================================================
SELECT
    d.id as document_id,
    d.title,
    d.source_url,
    p.key as project_key,
    pd.status as processing_status,
    COUNT(dv.id) as vector_count,
    MIN(dv.chunk_index) as first_chunk,
    MAX(dv.chunk_index) as last_chunk,
    CASE
        WHEN COUNT(dv.id) > 0 THEN
            CASE
                WHEN dv.embedding IS NOT NULL THEN 'Valid ✅'
                ELSE 'NULL embedding ⚠️'
            END
        ELSE 'No vectors ❌'
    END as embedding_status
FROM documents d
LEFT JOIN project_documents pd ON pd.document_id = d.id
LEFT JOIN projects p ON pd.project_id = p.id
LEFT JOIN document_vectors dv ON dv.project_document_id = pd.id
WHERE d.source_url LIKE '%arxiv.org%'
GROUP BY d.id, d.title, d.source_url, p.key, pd.status, dv.embedding
ORDER BY d.created_at DESC;

-- ====================================================================
-- 4. Check embedding dimensions (should be consistent)
-- ====================================================================
SELECT
    'Embedding Dimensions' as metric,
    MIN(array_length(embedding, 1)) as min_dim,
    MAX(array_length(embedding, 1)) as max_dim,
    AVG(array_length(embedding, 1))::int as avg_dim,
    CASE
        WHEN MIN(array_length(embedding, 1)) = MAX(array_length(embedding, 1))
        THEN 'Consistent ✅'
        ELSE 'INCONSISTENT ⚠️'
    END as consistency
FROM document_vectors
WHERE embedding IS NOT NULL;

-- ====================================================================
-- 5. Sample embedding values (check if non-zero)
-- ====================================================================
SELECT
    dv.id,
    d.title,
    dv.chunk_index,
    array_length(dv.embedding, 1) as dimension,
    dv.embedding[1:5] as first_5_values,
    CASE
        WHEN dv.embedding IS NULL THEN 'NULL ❌'
        WHEN array_length(dv.embedding, 1) < 100 THEN 'Too small ⚠️'
        ELSE 'OK ✅'
    END as status
FROM document_vectors dv
JOIN project_documents pd ON dv.project_document_id = pd.id
JOIN documents d ON pd.document_id = d.id
WHERE d.source_url LIKE '%arxiv.org%'
LIMIT 10;
