import { testDatabaseConnection } from '../config/database.js';
import { testRedisConnection } from '../config/queue.js';
import { HealthCheck } from '../types/schemas.js';

export const getHealthStatus = async (): Promise<HealthCheck> => {
  const [dbHealthy, redisHealthy] = await Promise.all([
    testDatabaseConnection(),
    testRedisConnection(),
  ]);

  const isHealthy = dbHealthy && redisHealthy;

  return {
    status: isHealthy ? 'healthy' : 'unhealthy',
    timestamp: new Date().toISOString(),
    services: {
      database: dbHealthy,
      redis: redisHealthy,
    },
  };
};
