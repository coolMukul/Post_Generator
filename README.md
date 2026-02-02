# Post Generator - Research Insight Platform

A multi-agent research insight generation platform built with Fastify, Python workers, LangGraph, and pgvector.

## Quick Start

### Prerequisites

- Node.js 22+ (you have v22.15.1 ✓)
- Python 3.11+
- PostgreSQL 15+ with pgvector extension
- Redis 7+

### Installation

1. **Clone and navigate to the repository:**
```bash
cd Post_Generator
```

2. **Copy environment file:**
```bash
cp .env.example .env
```
Edit `.env` with your actual configuration values.

3. **Initialize database:**
```bash
# Connect to PostgreSQL
psql -U postgres

# In psql prompt:
CREATE DATABASE post_generator;
\c post_generator
CREATE EXTENSION vector;

# Run the initialization script
\i scripts/init_db.sql
```

4. **Install Node.js dependencies:**
```bash
npm install -g pnpm  # If not already installed
pnpm install
```

5. **Install Python dependencies:**
```bash
cd packages/workers
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ../..
```

### Running the Application

**Terminal 1 - API Server:**
```bash
cd packages/api
pnpm dev
```
API will be available at: http://localhost:3201
Swagger docs at: http://localhost:3201/documentation

**Terminal 2 - Worker:**
```bash
cd packages/workers
source venv/bin/activate
python -m src.worker
```

**Terminal 3 - UI (Optional):**
```bash
cd packages/ui
pnpm dev
```
UI will be available at: http://localhost:3202

### Testing the Setup

1. **Check health:**
```bash
curl http://localhost:3201/health
```

2. **Submit a test job:**
```bash
curl -X POST http://localhost:3201/pdf/process \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/sample.pdf",
    "title": "Test Document"
  }'
```

3. **Check job status:**
```bash
curl http://localhost:3201/jobs/{job_id}
```

4. **Or use the UI:**
   - Navigate to http://localhost:3202/ingest
   - Submit a PDF URL and watch real-time progress

## Project Structure

```
post_generator/
├── packages/
│   ├── api/              # Fastify Node.js API (port 3201)
│   │   └── src/
│   │       ├── routes/   # API endpoints
│   │       ├── handlers/ # Business logic
│   │       ├── config/   # Configuration
│   │       └── types/    # TypeScript schemas
│   ├── ui/               # Next.js UI (port 3202)
│   │   └── app/
│   │       ├── ingest/   # PDF ingestion page
│   │       └── ...       # Other pages
│   └── workers/          # Python background workers
│       └── src/
│           ├── jobs/     # Job processors
│           ├── agents/   # LangGraph agents
│           ├── services/ # Business logic
│           └── repositories/ # Database layer
├── scripts/              # Database scripts
├── mukDocs/              # Documentation
└── .env                  # Environment variables
```

## API Endpoints

### Health
- `GET /health` - System health check
- `GET /ping` - Simple ping

### Jobs
- `GET /jobs` - List all jobs
- `GET /jobs/:jobId` - Get job status

### PDF Processing
- `POST /pdf/process` - Submit PDF for processing

### Query
- `POST /query` - Search documents (vector similarity)

## Development

### API Development
```bash
cd packages/api
pnpm dev      # Start with hot reload
pnpm test     # Run tests
pnpm lint     # Lint code
```

### Worker Development
```bash
cd packages/workers
source venv/bin/activate
python -m src.worker      # Start worker
pytest                    # Run tests
black src/                # Format code
ruff check src/           # Lint code
```

## Phase 1 Status

✅ Monorepo infrastructure
✅ Fastify API with Swagger
✅ BullMQ job queue setup
✅ PostgreSQL with pgvector
✅ Python workers with stubs
✅ Database schema
✅ Environment configuration

**Next:** Phase 2 - PDF Processing Implementation

## Documentation

- [Setup Guide](mukDocs/phase1-setup-guide.md) - Detailed setup instructions
- [Planning Doc](mukDocs/planning-doc-refined.md) - Project roadmap

## Tech Stack

- **API:** Fastify, TypeScript, BullMQ, Zod
- **UI:** Next.js, React, TypeScript, Tailwind CSS
- **Workers:** Python, LangGraph, LangChain
- **Database:** PostgreSQL, pgvector
- **Queue:** Redis, BullMQ
- **AI:** OpenAI, LlamaParse

## Port Configuration

- **API Server:** 3201
- **UI Server:** 3202
- **PostgreSQL:** 5432
- **Redis:** 6379

_(Ports 3000-3002 and 3100-3102 are reserved for other projects)_

## License

MIT
