# Phase 1: Initial Setup Guide

## Prerequisites

Before starting, ensure you have the following installed:

- **Node.js**: v22.15.1 (as shown in your environment)
- **Python**: 3.11+ (for workers and agents)
- **PostgreSQL**: 15+ with pgvector extension
- **Redis**: 7+ (for BullMQ job queue)
- **pnpm** or **npm**: Package manager

## Project Structure

```
post_generator/
├── packages/
│   ├── api/                    # Fastify Node.js API
│   │   ├── src/
│   │   │   ├── routes/        # API routes
│   │   │   ├── handlers/      # Business logic handlers
│   │   │   ├── types/         # Shared TypeScript types
│   │   │   ├── config/        # Configuration
│   │   │   └── server.ts      # Main server file
│   │   ├── package.json
│   │   └── tsconfig.json
│   ├── workers/               # Python background workers
│   │   ├── src/
│   │   │   ├── jobs/          # BullMQ job processors
│   │   │   ├── agents/        # LangGraph agents
│   │   │   ├── services/      # Business logic
│   │   │   └── repositories/  # Data access layer
│   │   ├── pyproject.toml
│   │   └── requirements.txt
│   └── shared/                # Shared types and schemas
│       └── types/
├── scripts/                   # Database migrations, utilities
├── mukDocs/                   # Documentation
├── .env                       # Environment variables
├── .gitignore
├── package.json               # Root workspace config
├── pnpm-workspace.yaml        # Workspace configuration
└── README.md
```

## Initial Setup Commands

### 1. Initialize the Monorepo

```bash
# Initialize root package.json for workspace
npm init -y

# Create workspace configuration
cat > pnpm-workspace.yaml << EOF
packages:
  - 'packages/*'
EOF
```

### 2. PostgreSQL Setup with pgvector

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL service
sudo service postgresql start

# Install pgvector extension
sudo apt install postgresql-15-pgvector

# Connect to PostgreSQL
sudo -u postgres psql

# In PostgreSQL prompt:
CREATE DATABASE post_generator;
\c post_generator
CREATE EXTENSION vector;

# Create user (optional)
CREATE USER postgenerator WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE post_generator TO postgenerator;
```

### 3. Redis Setup

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

### 4. Database Schema Creation

Run the following SQL to create the required tables:

```sql
-- Documents table
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT,
    checksum VARCHAR(64) UNIQUE NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documents_checksum ON documents(checksum);
CREATE INDEX idx_documents_created_at ON documents(created_at);

-- Vectors table
CREATE TABLE vectors (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    context_summary TEXT,
    embedding VECTOR(1536),
    token_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vectors_document_id ON vectors(document_id);
CREATE INDEX idx_vectors_embedding ON vectors USING ivfflat (embedding vector_cosine_ops);
```

### 5. Environment Configuration

Create a `.env` file in the root directory:

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
API_PORT=3000
API_HOST=0.0.0.0
NODE_ENV=development

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# LlamaParse
LLAMA_CLOUD_API_KEY=your_llamaparse_api_key

# Worker Configuration
WORKER_CONCURRENCY=5
```

### 6. Install Node.js Dependencies

```bash
# Install pnpm if not already installed
npm install -g pnpm

# In the root directory
pnpm install
```

### 7. Install Python Dependencies

```bash
# Create virtual environment for workers
cd packages/workers
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## Running the Project

### Start the API Server

```bash
# From root directory
cd packages/api
pnpm dev
```

The API will be available at `http://localhost:3000`

### Start the Workers

```bash
# From root directory
cd packages/workers
source venv/bin/activate
python -m src.worker
```

### View API Documentation

Once the API is running, access Swagger documentation at:
```
http://localhost:3000/documentation
```

## Verify Setup

### Check Database Connection

```bash
psql -U postgenerator -d post_generator -h localhost

# In psql prompt:
\dt  # List tables
SELECT * FROM pg_extension WHERE extname = 'vector';  # Verify pgvector
```

### Check Redis Connection

```bash
redis-cli ping
redis-cli info
```

### Test API Health

```bash
curl http://localhost:3000/health
```

## Development Workflow

1. **Start services in order:**
   - PostgreSQL
   - Redis
   - API Server
   - Workers

2. **Development commands:**
   ```bash
   # API development with hot reload
   cd packages/api && pnpm dev

   # Run API tests
   cd packages/api && pnpm test

   # Run worker tests
   cd packages/workers && pytest

   # Linting
   cd packages/api && pnpm lint
   ```

3. **Database migrations:**
   ```bash
   # Create migration
   cd scripts
   # Add SQL files to migrations folder
   ```

## Troubleshooting

### PostgreSQL Connection Issues
- Verify PostgreSQL is running: `sudo service postgresql status`
- Check pg_hba.conf for authentication settings
- Ensure user has proper permissions

### Redis Connection Issues
- Verify Redis is running: `sudo service redis-server status`
- Check Redis logs: `sudo tail -f /var/log/redis/redis-server.log`

### pgvector Extension Issues
- Ensure PostgreSQL version 11+
- Install pgvector: `sudo apt install postgresql-15-pgvector`
- Restart PostgreSQL after installation

### Node.js Version Issues
- Use nvm to switch versions: `nvm use 22.15.1`
- Verify: `node --version`

## Next Steps

After completing the setup:
1. Test all endpoints using Swagger UI
2. Submit a test job through the API
3. Verify worker processes the job
4. Check database for stored results
5. Proceed to Phase 2: PDF Processing Implementation

## Additional Resources

- [Fastify Documentation](https://www.fastify.io/)
- [BullMQ Documentation](https://docs.bullmq.io/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
