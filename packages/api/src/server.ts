import Fastify from 'fastify';
import cors from '@fastify/cors';
import swagger from '@fastify/swagger';
import swaggerUi from '@fastify/swagger-ui';
import { env } from './config/env.js';
import { closeDatabaseConnection, testDatabaseConnection } from './config/database.js';
import { closeQueueConnections, testRedisConnection } from './config/queue.js';
import { healthRoutes } from './routes/health.routes.js';
import { jobRoutes } from './routes/job.routes.js';
import { pdfRoutes } from './routes/pdf.routes.js';
import { queryRoutes } from './routes/query.routes.js';

// Create Fastify instance
const fastify = Fastify({
  logger: {
    level: env.NODE_ENV === 'production' ? 'info' : 'debug',
    transport: env.NODE_ENV === 'development' ? {
      target: 'pino-pretty',
      options: {
        translateTime: 'HH:MM:ss Z',
        ignore: 'pid,hostname',
        colorize: true
      }
    } : undefined
  }
});

// Register plugins
async function registerPlugins() {
  // CORS
  await fastify.register(cors, {
    origin: true,
    credentials: true
  });

  // Swagger documentation
  await fastify.register(swagger, {
    openapi: {
      info: {
        title: 'Post Generator API',
        description: 'Research insight generation platform with multi-agent workflows',
        version: '1.0.0'
      },
      // Use a browser-reachable host for Swagger UI (don't expose 0.0.0.0)
      servers: [
        {
          url: `http://${env.API_HOST === '0.0.0.0' ? 'localhost' : env.API_HOST}:${env.API_PORT}`,
          description: 'Development server'
        }
      ],
      tags: [
        { name: 'Health', description: 'Health check endpoints' },
        { name: 'Jobs', description: 'Job management endpoints' },
        { name: 'PDF', description: 'PDF processing endpoints' },
        { name: 'Query', description: 'Vector search endpoints' }
      ]
    }
  });

  // Swagger UI
  await fastify.register(swaggerUi, {
    routePrefix: '/documentation',
    uiConfig: {
      docExpansion: 'list',
      deepLinking: true
    },
    staticCSP: true
  });
}

// Register routes
async function registerRoutes() {
  await fastify.register(healthRoutes);
  await fastify.register(jobRoutes);
  await fastify.register(pdfRoutes);
  await fastify.register(queryRoutes);
}

// Startup checks
async function performStartupChecks() {
  fastify.log.info('Performing startup checks...');

  const [dbHealthy, redisHealthy] = await Promise.all([
    testDatabaseConnection(),
    testRedisConnection()
  ]);

  if (!dbHealthy) {
    fastify.log.error('Database connection failed');
    throw new Error('Database connection failed');
  }

  if (!redisHealthy) {
    fastify.log.error('Redis connection failed');
    throw new Error('Redis connection failed');
  }

  fastify.log.info('All startup checks passed');
}

// Graceful shutdown
async function gracefulShutdown() {
  fastify.log.info('Shutting down gracefully...');

  try {
    await Promise.all([
      fastify.close(),
      closeDatabaseConnection(),
      closeQueueConnections()
    ]);
    fastify.log.info('Shutdown complete');
    process.exit(0);
  } catch (error) {
    fastify.log.error('Error during shutdown:', error);
    process.exit(1);
  }
}

// Start server
async function start() {
  try {
    // Register plugins and routes
    await registerPlugins();
    await registerRoutes();

    // Perform startup checks
    await performStartupChecks();

    // Start listening
    await fastify.listen({
      port: env.API_PORT,
      host: env.API_HOST
    });

    fastify.log.info(`Server listening on http://${env.API_HOST}:${env.API_PORT}`);
    fastify.log.info(`Swagger documentation available at http://${env.API_HOST}:${env.API_PORT}/documentation`);

    // Setup graceful shutdown
    process.on('SIGTERM', gracefulShutdown);
    process.on('SIGINT', gracefulShutdown);

  } catch (error) {
    fastify.log.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Start the server
start();
