import { FastifyInstance } from 'fastify';
import { searchVectors } from '../handlers/query.handler.js';
import { QueryRequestSchema } from '../types/schemas.js';

export async function queryRoutes(fastify: FastifyInstance) {
  fastify.post('/query', {
    schema: {
      description: 'Search documents using vector similarity',
      tags: ['Query'],
      body: {
        type: 'object',
        required: ['query'],
        properties: {
          query: { type: 'string', minLength: 1, description: 'Search query' },
          limit: {
            type: 'number',
            minimum: 1,
            maximum: 100,
            default: 10,
            description: 'Number of results'
          },
          document_id: { type: 'number', description: 'Filter by specific document' }
        }
      },
      response: {
        200: {
          description: 'Search results',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  results: {
                    type: 'array',
                    items: {
                      type: 'object',
                      properties: {
                        content: { type: 'string' },
                        context_summary: { type: 'string', nullable: true },
                        similarity: { type: 'number' },
                        document_id: { type: 'number' },
                        chunk_index: { type: 'number' }
                      }
                    }
                  },
                  query: { type: 'string' },
                  total: { type: 'number' }
                }
              }
            }
          }
        },
        400: {
          description: 'Invalid request',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  error: { type: 'string' }
                }
              }
            }
          }
        }
      }
    },
    handler: async (request, reply) => {
      try {
        const data = QueryRequestSchema.parse(request.body);
        const result = await searchVectors(data);
        return reply.send(result);
      } catch (error: any) {
        return reply.code(400).send({ error: error.message });
      }
    }
  });
}
