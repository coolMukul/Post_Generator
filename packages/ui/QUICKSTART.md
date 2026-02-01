# Quick Start: Test Phase 2 Ingestion UI

## 🚀 3-Minute Setup

### 1. Start Services (3 terminals)

```bash
# Terminal 1: Worker
cd packages/research-workers
pnpm dev

# Terminal 2: API
cd packages/research-api
pnpm dev

# Terminal 3: UI
cd packages/research-ui
pnpm dev
```

### 2. Open Browser

http://localhost:3200/ingest

### 3. Test with arXiv Paper

1. Click "📎 Submit URL"
2. Paste: `https://arxiv.org/pdf/1706.03762.pdf` (Transformers paper)
3. Click "🚀 Ingest Document"
4. Watch real-time progress!

## ✅ What to Expect

You'll see the job progress through these steps:
- ⏳ WAITING → ⟳ ACTIVE (5-80%) → ✓ COMPLETED (100%)

Processing time: ~2-5 minutes depending on paper length and API speed.

## 🔍 Verify Success

Check database:
```sql
SELECT COUNT(*) FROM document_vectors;
-- Should show chunks (typically 20-50 per paper)
```

## 📋 Prerequisites

- ✓ PostgreSQL running with schema loaded
- ✓ Redis running  
- ✓ `.env.local` files configured with API keys
- ✓ All packages built

See [TESTING-PHASE-2.md](./TESTING-PHASE-2.md) for detailed setup.

## 🎯 URLs

- UI: http://localhost:3200
- API: http://localhost:3101
- API Docs: http://localhost:3101/docs
