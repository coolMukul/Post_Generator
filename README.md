# Post Generator - Research Insight Platform

A multi-agent research insight generation platform built with Fastify, Python workers, LangGraph, and pgvector.

## Quick Start

### Prerequisites

- Node.js 22+ (you have v22.15.1 ✓)
- Python 3.11+
- PostgreSQL 15+ with pgvector extension
- Redis 7+

### Installation

#### For Windows (PowerShell)

1. **Clone and navigate to the repository:**
```powershell
cd Post_Generator
```

2. **Copy environment file:**
```powershell
Copy-Item .env.example .env
```
Edit `.env` with your actual configuration values.

3. **Create UI environment file:**
```powershell
Copy-Item packages\ui\.env.example packages\ui\.env
# Or manually create packages\ui\.env with:
# NEXT_PUBLIC_API_URL=http://localhost:3201
```

4. **Initialize database:**
```powershell
# Connect to PostgreSQL (adjust path if needed)
psql -U postgres

# In psql prompt:
CREATE DATABASE post_generator;
\c post_generator
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

# Run the initialization script
\i scripts/init_db.sql
```

5. **Install Node.js dependencies:**
```powershell
npm install -g pnpm  # If not already installed
pnpm install
```

6. **Install Python dependencies:**
```powershell
cd packages\workers
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
cd ..\..
```

#### For Linux/Mac (Bash)

1. **Clone and navigate:**
```bash
cd Post_Generator
```

2. **Copy environment files:**
```bash
cp .env.example .env
cp packages/ui/.env.example packages/ui/.env
```

3. **Initialize database:**
```bash
psql -U postgres -c "CREATE DATABASE post_generator;"
psql -U postgres -d post_generator < scripts/init_db.sql
```

4. **Install dependencies:**
```bash
npm install -g pnpm
pnpm install
cd packages/workers
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ../..
```

### Running the Application

#### Windows (PowerShell)

**Terminal 1 - API Server:**
```powershell
cd packages\api
pnpm dev
```

**Terminal 2 - Worker:**
```powershell
cd packages\workers
.\venv\Scripts\activate
python -m src.worker
```

**Terminal 3 - UI:**
```powershell
cd packages\ui
pnpm dev
```

#### Linux/Mac (Bash)

**Terminal 1 - API Server:**
```bash
cd packages/api
pnpm dev
```

**Terminal 2 - Worker:**
```bash
cd packages/workers
source venv/bin/activate
python -m src.worker
```

**Terminal 3 - UI:**
```bash
cd packages/ui
pnpm dev
```

**Access Points:**
- API: http://localhost:3201
- Swagger docs: http://localhost:3201/documentation
- UI: http://localhost:3202

### Testing the Setup

#### Windows (PowerShell)

1. **Check health:**
```powershell
curl http://localhost:3201/health
```

2. **Submit a test job:**
```powershell
$body = @{
    url = "https://arxiv.org/pdf/2301.00001.pdf"
    title = "Test Document"
    project_key = "researchpaper"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:3201/pdf/process" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

3. **Check job status:**
```powershell
curl http://localhost:3201/jobs/YOUR_JOB_ID_HERE
```

#### Linux/Mac (Bash)

1. **Check health:**
```bash
curl http://localhost:3201/health
```

2. **Submit a test job:**
```bash
curl -X POST http://localhost:3201/pdf/process \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://arxiv.org/pdf/2301.00001.pdf",
    "title": "Test Document",
    "project_key": "researchpaper"
  }'
```

3. **Check job status:**
```bash
curl http://localhost:3201/jobs/YOUR_JOB_ID_HERE
```

#### Using the UI (All Platforms)

1. Navigate to http://localhost:3202/ingest
2. Paste a PDF URL (e.g., arXiv paper)
3. Add an optional title
4. Click "Ingest Document"
5. Watch real-time job progress

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
