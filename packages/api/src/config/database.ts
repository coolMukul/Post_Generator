import pg from 'pg';
import { getDatabaseUrl, env } from './env.js';

const { Pool } = pg;

// Create PostgreSQL connection pool
// REMOVED: database config migrated to Python API (packages/api/app)

// Removed pool initialization

// Test database connection
// Removed testDatabaseConnection function

// Graceful shutdown
// Removed closeDatabaseConnection function
