# Phase 1: Initial Setup Guide

## Prerequisites

Before starting, ensure you have the following installed:

- **Node.js**: v22.15.1+ (as shown in your environment)
- **Python**: 3.11+ (for workers and agents)
- **PostgreSQL**: 15+ with pgvector extension
- **Redis**: 7+ (for BullMQ job queue)
- **pnpm** or **npm**: Package manager

## Project Structure

```
post_generator/
├── packages/
│   ├── api/                    # Fastify Node.js API (port 3201)
│   │   ├── src/
│   │   │   ├── routes/        # API routes
│   │   │   ├── handlers/      # Business logic handlers
│   │   │   ├── types/         # Shared TypeScript types/schemas
│   │   │   ├── config/        # Configuration
│   │   │   └── server.ts      # Main server file
│   │   ├── package.json
│   │   └── tsconfig.json
│   ├── ui/                     # Next.js UI (port 3202)
│   │   ├── app/
│   │   │   ├── ingest/        # PDF ingestion page
│   │   │   ├── globals.css
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   ├── package.json
│   │   ├── .env               # UI environment config
│   │   └── tsconfig.json
│   └── workers/               # Python background workers
│       ├── src/
│       │   ├── jobs/          # BullMQ job processors
│       │   ├── agents/        # LangGraph agents
│       │   ├── services/      # Business logic
│       │   ├── repositories/  # Data access layer
│       │   ├── config.py      # Worker configuration
│       │   └── worker.py      # Main worker file
│       ├── pyproject.toml
│       └── requirements.txt
├── scripts/                   # Database migrations, utilities
│   └── init_db.sql            # Database initialization script
├── mukDocs/                   # Documentation
├── .env                       # Environment variables
├── .env.example               # Environment template
├── .gitignore
├── package.json               # Root workspace config
├── pnpm-workspace.yaml        # Workspace configuration
└── README.md
```

## Initial Setup Commands

### For Windows (PowerShell)

#### 1. Initialize the Monorepo

Already set up in this repository. To verify:
```powershell
Get-Content pnpm-workspace.yaml
```

#### 2. PostgreSQL Setup with pgvector

```powershell
# Install PostgreSQL from https://www.postgresql.org/download/windows/
# Or using Chocolatey:
choco install postgresql

# Start PostgreSQL service (usually auto-starts)
# Verify it's running in Services app or:
Get-Service postgresql*

# Install pgvector extension
# Download from: https://github.com/pgvector/pgvector/releases
# Follow Windows installation instructions

# Connect to PostgreSQL
psql -U postgres

# In PostgreSQL prompt:
CREATE DATABASE post_generator;
\c post_generator
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

# Create user (optional but recommended)
CREATE USER postgenerator WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE post_generator TO postgenerator;
ALTER DATABASE post_generator OWNER TO postgenerator;

# Run initialization script
\i scripts/init_db.sql

# Verify tables were created
\dt
```

#### 3. Redis Setup

```powershell
# Install Redis using WSL2 or from:
# https://github.com/microsoftarchive/redis/releases

# Or using Chocolatey:
choco install redis-64

# Start Redis (if using native Windows version)
redis-server

# Or if using WSL2:
wsl
sudo service redis-server start
exit

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

#### 4. Environment Configuration

```powershell
# Copy environment files
Copy-Item .env.example .env
Copy-Item packages\ui\.env.example packages\ui\.env

# Edit .env with your actual values
notepad .env
```

Edit `.env` with your configuration:
```env
# Database
DATABASE_URL=postgresql://postgenerator:your_password@localhost:5432/post_generator
DB_HOST=localhost
DB_PORT=5432
DB_NAME=post_generator
DB_USER=postgenerator
DB_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# API Configuration
API_PORT=3201
API_HOST=0.0.0.0
NODE_ENV=development

# Embedding Provider Configuration
EMBEDDING_PROVIDER=gemini                    # Options: gemini, openai (default: gemini)
EMBEDDING_MODEL=gemini-embedding-001         # Model name for chosen provider
EMBEDDING_DIMENSION=1536                      # Vector dimension (must match DB schema)

# AI API Keys
GEMINI_API_KEY=your_gemini_api_key           # Required if EMBEDDING_PROVIDER=gemini
OPENAI_API_KEY=sk-your_openai_api_key        # Required if EMBEDDING_PROVIDER=openai

# LlamaParse
LLAMA_CLOUD_API_KEY=llx-your_llamaparse_api_key

# Worker Configuration
WORKER_CONCURRENCY=5
```

Edit `packages/ui/.env`:
```env
NEXT_PUBLIC_API_URL=http://localhost:3201
```

#### 5. Install Node.js Dependencies

```powershell
# Install pnpm if not already installed
npm install -g pnpm

# In the root directory
pnpm install
```

#### 6. Install Python Dependencies

```powershell
# Create virtual environment for workers
cd packages\workers
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Return to root
cd ..\..
```

### For Linux/Mac (Bash)

#### 1. Initialize the Monorepo

Already set up in this repository. To verify:
```bash
cat pnpm-workspace.yaml
```

#### 2. PostgreSQL Setup with pgvector

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib

# Install pgvector extension
sudo apt install postgresql-15-pgvector

# Start PostgreSQL service
sudo service postgresql start

# Connect to PostgreSQL
sudo -u postgres psql

# In PostgreSQL prompt:
CREATE DATABASE post_generator;
\c post_generator
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

# Create user (optional but recommended)
CREATE USER postgenerator WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE post_generator TO postgenerator;
ALTER DATABASE post_generator OWNER TO postgenerator;

# Exit psql and run initialization script
\q
psql -U postgres -d post_generator < scripts/init_db.sql

# Verify tables
psql -U postgres -d post_generator -c "\dt"
```

#### 3. Redis Setup

```bash
# Install Redis (Ubuntu/Debian)
sudo apt update
sudo apt install redis-server

# Start Redis service
sudo service redis-server start

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

#### 4. Environment Configuration

```bash
# Copy environment files
cp .env.example .env
cp packages/ui/.env.example packages/ui/.env

# Edit files with your actual values
nano .env
nano packages/ui/.env
```

#### 5. Install Node.js Dependencies

```bash
# Install pnpm if not already installed
npm install -g pnpm

# In the root directory
pnpm install
```

#### 6. Install Python Dependencies

```bash
# Create virtual environment for workers
cd packages/workers
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Return to root
cd ../..
```

## Database Schema

The current schema uses a **multi-project design** with UUID primary keys:

### Core Tables:
- **documents**: Generic document storage (UUID id)
- **projects**: Project/use-case definitions (UUID id)
- **project_documents**: Many-to-many linking (UUID id)
- **document_vectors**: Vector embeddings per project (UUID id)

### Key Features:
- UUID-based primary keys for distributed systems
- Multi-tenancy support via projects table
- Parsing failure tracking (attempts, failures, errors)
- Flexible JSONB metadata at all levels
- pgvector for similarity search

See `scripts/init_db.sql` for the complete schema.

## Running the Project

### Windows (PowerShell)

**Terminal 1 - API Server:**
```powershell
cd packages\api
.\venv\Scripts\activate
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

### Linux/Mac (Bash)

**Terminal 1 - API Server:**
```bash
cd packages/api
source venv/bin/activate
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

### Access Points

- **API**: http://localhost:3201
- **Swagger Documentation**: http://localhost:3201/documentation
- **UI**: http://localhost:3202

## Verify Setup

### Check Database Connection

**PowerShell:**
```powershell
psql -U postgenerator -d post_generator -h localhost

# In psql prompt:
\dt  # List tables (should show: documents, projects, project_documents, document_vectors)
SELECT * FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp');  # Verify extensions
SELECT * FROM projects;  # Should show 'researchpaper' project
```

**Bash:**
```bash
psql -U postgenerator -d post_generator -h localhost
# Same commands as above
```

### Check Redis Connection

```powershell
redis-cli ping
redis-cli info server
```

### Test API Health

**PowerShell:**
```powershell
curl http://localhost:3201/health
```

**Bash:**
```bash
curl http://localhost:3201/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "services": {
    "database": true,
    "redis": true
  }
}
```

### Test API with PDF Processing

**PowerShell:**
```powershell
$body = @{
    url = "https://arxiv.org/pdf/2301.00001.pdf"
    title = "Test Paper"
    project_key = "researchpaper"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:3201/pdf/process" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

**Bash:**
```bash
curl -X POST http://localhost:3201/pdf/process \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://arxiv.org/pdf/2301.00001.pdf",
    "title": "Test Paper",
    "project_key": "researchpaper"
  }'
```

### Test UI

1. Navigate to http://localhost:3202/ingest
2. Paste an arXiv PDF URL
3. Add an optional title
4. Click "Ingest Document"
5. Watch real-time job progress

## Development Workflow

### 1. Start Services in Order

**Required:**
- PostgreSQL
- Redis

**Your Application:**
- API Server (port 3201)
- Worker (processes jobs)
- UI (port 3202) - optional

### 2. Development Commands

**API Development:**
```powershell
# PowerShell
cd packages\api
.\venv\Scripts\activate
pnpm dev          # Hot reload
pnpm build        # Production build
pnpm lint         # Linting
```

**Worker Development:**
```powershell
# PowerShell
cd packages\workers
.\venv\Scripts\activate
python -m src.worker    # Start worker
pytest                   # Run tests (when added)
black src/               # Format code
ruff check src/          # Lint code
```

**UI Development:**
```powershell
# PowerShell
cd packages\ui
pnpm dev          # Hot reload
pnpm build        # Production build
pnpm lint         # Linting
```

### 3. Database Operations

**View Data:**
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
  pd.status,
  pd.added_at
FROM project_documents pd
JOIN projects p ON pd.project_id = p.id
JOIN documents d ON pd.document_id = d.id;

-- Check vector counts
SELECT
  COUNT(*) as vector_count,
  d.title
FROM document_vectors dv
JOIN project_documents pd ON dv.project_document_id = pd.id
JOIN documents d ON pd.document_id = d.id
GROUP BY d.title;
```

## Troubleshooting

### PostgreSQL Connection Issues
- **Windows**: Check if PostgreSQL service is running in Services app
- **Linux**: `sudo service postgresql status`
- Check `pg_hba.conf` for authentication settings
- Ensure user has proper permissions
- Verify DATABASE_URL in `.env` is correct

### Redis Connection Issues
- **Windows**: Check if Redis service is running (or WSL2 Redis)
- **Linux**: `sudo service redis-server status`
- Check Redis logs for errors
- Verify REDIS_HOST and REDIS_PORT in `.env`

### pgvector Extension Issues
- Ensure PostgreSQL version 11+
- **Windows**: Download from GitHub releases
- **Linux**: `sudo apt install postgresql-15-pgvector`
- Restart PostgreSQL after installation
- Verify: `SELECT * FROM pg_extension WHERE extname = 'vector';`

### uuid-ossp Extension Issues
- Usually included with PostgreSQL
- Enable with: `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`
- Verify: `SELECT * FROM pg_extension WHERE extname = 'uuid-ossp';`

### Node.js Version Issues
- Use nvm to switch versions: `nvm use 22.15.1`
- Verify: `node --version`
- Clear node_modules if changing versions: `pnpm install --force`

### Python Virtual Environment Issues
- **Windows**: Ensure using `.\venv\Scripts\activate` (not `source`)
- **Linux/Mac**: Ensure using `source venv/bin/activate`
- Verify: `which python` (should show venv path)
- Recreate if corrupted: `python -m venv venv --clear`

### Port Already in Use
- Ports 3000-3002 and 3100-3102 are reserved for other projects
- This project uses:
  - **3201**: API
  - **3202**: UI
- Find what's using a port:
  - **Windows**: `netstat -ano | findstr :3201`
  - **Linux**: `lsof -i :3201`

### Worker Not Processing Jobs
- Check Redis connection
- Verify worker is running and connected to Redis
- Check BullMQ queue names match between API and worker
- Look for errors in worker terminal output

## Port Configuration

This project uses the following ports:

- **API Server**: 3201
- **UI Server**: 3202
- **PostgreSQL**: 5432 (default)
- **Redis**: 6379 (default)

**Note**: Ports 3000-3002 and 3100-3102 are reserved for other projects.

## Next Steps

After completing the setup:

1. ✅ Verify all services are running
2. ✅ Test API health endpoint
3. ✅ Test UI loads correctly
4. ⚠️ **Update Python worker repositories** (see `mukDocs/schema-migration-guide.md`)
5. Test PDF processing end-to-end
6. Verify data is stored correctly in database
7. Test vector search functionality
8. Proceed to Phase 2: Advanced Features

## Important Migration Note

⚠️ **The Python workers need updating** to work with the new UUID-based multi-project schema. See the detailed guide:

📖 **[Schema Migration Guide](./schema-migration-guide.md)**

This guide covers:
- Required changes to document_repository.py
- Required changes to vector_repository.py
- Required changes to pdf_processor.py
- Testing procedures

## Additional Resources

- [Fastify Documentation](https://www.fastify.io/)
- [Next.js Documentation](https://nextjs.org/docs)
- [BullMQ Documentation](https://docs.bullmq.io/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [PostgreSQL UUID Documentation](https://www.postgresql.org/docs/current/datatype-uuid.html)
