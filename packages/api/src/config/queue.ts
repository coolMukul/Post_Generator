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
  MAIN_PROCESSING: 'main-processing-queue',
  VECTOR_GENERATION: 'vector-generation',
  AGENT_TASKS: 'agent-tasks',
  HYBRID_RETRIEVAL: 'hybrid-retrieval'
} as const;

// Create queues
export const mainProcessingQueue = new Queue(QUEUE_NAMES.MAIN_PROCESSING, {
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

export const hybridRetrievalQueue = new Queue(QUEUE_NAMES.HYBRID_RETRIEVAL, {
  connection: redisConnection,
  defaultJobOptions: {
    attempts: 2,
    backoff: {
      type: 'exponential',
      delay: 1000,
    },
    removeOnComplete: {
      count: 50,
      age: 3600, // 1 hour
    },
    removeOnFail: {
      count: 100,
    },
  },
});

// Queue events for monitoring
export const mainProcessingEvents = new QueueEvents(QUEUE_NAMES.MAIN_PROCESSING, {
  connection: redisConnection,
});

// Graceful shutdown
export const closeQueueConnections = async (): Promise<void> => {
  await Promise.all([
    mainProcessingQueue.close(),
    vectorGenerationQueue.close(),
    agentTasksQueue.close(),
    hybridRetrievalQueue.close(),
    mainProcessingEvents.close(),
    redisClient.quit(),
  ]);
};
