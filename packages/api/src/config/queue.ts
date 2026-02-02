import { Queue, QueueEvents } from 'bullmq';
import Redis from 'ioredis';
import { env } from './env.js';

// Redis connection configuration
const redisConnection = {
  host: env.REDIS_HOST,
  port: env.REDIS_PORT,
  password: env.REDIS_PASSWORD,
  maxRetriesPerRequest: null,
};

// Create Redis client for status checks
export const redisClient = new Redis(redisConnection);

// Test Redis connection
export const testRedisConnection = async (): Promise<boolean> => {
  try {
    await redisClient.ping();
    return true;
  } catch (error) {
    console.error('Redis connection failed:', error);
    return false;
  }
};

// Queue names
export const QUEUE_NAMES = {
  PDF_PROCESSING: 'pdf-processing',
  VECTOR_GENERATION: 'vector-generation',
  AGENT_TASKS: 'agent-tasks'
} as const;

// Create queues
export const pdfProcessingQueue = new Queue(QUEUE_NAMES.PDF_PROCESSING, {
  connection: redisConnection,
  defaultJobOptions: {
    attempts: 3,
    backoff: {
      type: 'exponential',
      delay: 2000,
    },
    removeOnComplete: {
      count: 100,
      age: 24 * 3600, // 24 hours
    },
    removeOnFail: {
      count: 1000,
    },
  },
});

export const vectorGenerationQueue = new Queue(QUEUE_NAMES.VECTOR_GENERATION, {
  connection: redisConnection,
  defaultJobOptions: {
    attempts: 3,
    backoff: {
      type: 'exponential',
      delay: 2000,
    },
  },
});

export const agentTasksQueue = new Queue(QUEUE_NAMES.AGENT_TASKS, {
  connection: redisConnection,
  defaultJobOptions: {
    attempts: 2,
    backoff: {
      type: 'exponential',
      delay: 5000,
    },
  },
});

// Queue events for monitoring
export const pdfProcessingEvents = new QueueEvents(QUEUE_NAMES.PDF_PROCESSING, {
  connection: redisConnection,
});

// Graceful shutdown
export const closeQueueConnections = async (): Promise<void> => {
  await Promise.all([
    pdfProcessingQueue.close(),
    vectorGenerationQueue.close(),
    agentTasksQueue.close(),
    pdfProcessingEvents.close(),
    redisClient.quit(),
  ]);
};
