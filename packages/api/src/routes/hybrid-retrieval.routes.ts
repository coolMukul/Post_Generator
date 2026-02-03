import { FastifyInstance } from 'fastify';
import { performHybridSearch } from '../handlers/hybrid-retrieval.handler.js';
import { HybridRetrievalRequestSchema } from '../types/schemas.js';

export async function hybridRetrievalRoutes(fastify: FastifyInstance) {
  fastify.post('/hybrid-retrieval', {
    schema: {
      description: 'Perform hybrid retrieval combining vector and keyword search',
      tags: ['Hybrid Retrieval'],
      body: {
        type: 'object',
        required: ['query'],
        properties: {
          query: {
            type: 'string',
            minLength: 1,
            description: 'Search query'
          },
          project_key: {
            type: 'string',
            default: 'researchpaper',
            description: 'Project key to search within'
          },
          limit: {
            type: 'number',
            minimum: 1,
            maximum: 100,
            default: 20,
            description: 'Maximum number of results'
          },
          min_score: {
            type: 'number',
            minimum: 0,
            maximum: 1,
            default: 0.3,
            description: 'Minimum score threshold (0-1)'
          },
          vector_weight: {
            type: 'number',
            minimum: 0,
            maximum: 1,
            default: 0.7,
            description: 'Weight for vector search results (0-1)'
          },
          keyword_weight: {
            type: 'number',
            minimum: 0,
            maximum: 1,
            default: 0.3,
            description: 'Weight for keyword search results (0-1)'
          },
          rrf_k: {
            type: 'number',
            minimum: 1,
            default: 60,
            description: 'RRF constant - higher values make ranking more conservative'
          }
        }
      },
      response: {
        200: {
          description: 'Hybrid search results',
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
                        id: { type: 'string', format: 'uuid' },
                        document_id: { type: 'string', format: 'uuid' },
                        chunk_index: { type: 'number' },
                        content: { type: 'string' },
                        context_summary: { type: ['string', 'null'] },
                        score: { type: 'number' },
                        metadata: { type: 'object' },
                        rank_source: { type: 'string', enum: ['vector', 'keyword', 'hybrid'] },
                        document_title: { type: 'string' }
                      }
                    }
                  },
                  query: { type: 'string' },
                  project_key: { type: 'string' },
                  total: { type: 'number' },
                  config: {
                    type: 'object',
                    properties: {
                      vector_weight: { type: 'number' },
                      keyword_weight: { type: 'number' },
                      rrf_k: { type: 'number' }
                    }
                  }
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
        const data = HybridRetrievalRequestSchema.parse(request.body);
        const result = await performHybridSearch(data);
        return reply.send(result);
      } catch (error: any) {
        fastify.log.error('Hybrid search error:', error);
        return reply.code(400).send({ error: error.message });
      }
    }
  });
}
