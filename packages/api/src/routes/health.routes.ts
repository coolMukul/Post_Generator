import { FastifyInstance } from 'fastify';
import { getHealthStatus } from '../handlers/health.handler.js';

export async function healthRoutes(fastify: FastifyInstance) {
  fastify.get('/health', {
    schema: {
      description: 'Health check endpoint',
      tags: ['Health'],
      response: {
        200: {
          description: 'Health status',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  status: { type: 'string', enum: ['healthy', 'unhealthy'] },
                  timestamp: { type: 'string' },
                  services: {
                    type: 'object',
                    properties: {
                      database: { type: 'boolean' },
                      redis: { type: 'boolean' }
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    handler: async (_request, reply) => {
      const health = await getHealthStatus();
      return reply.code(health.status === 'healthy' ? 200 : 503).send(health);
    }
  });

  fastify.get('/ping', {
    schema: {
      description: 'Simple ping endpoint',
      tags: ['Health'],
      response: {
        200: {
          description: 'Pong response',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  message: { type: 'string' }
                }
              }
            }
          }
        }
      }
    },
    handler: async (_request, reply) => {
      return reply.send({ message: 'pong' });
    }
  });
}
