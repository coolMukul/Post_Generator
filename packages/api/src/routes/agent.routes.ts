import { FastifyInstance } from 'fastify';
import {
  submitAgentJob,
  submitResearchQueryJob,
  submitInsightExtractionJob,
  submitLinkedInPostJob,
  submitContentWorkflowJob,
} from '../handlers/agent.handler.js';
import {
  AgentType,
  ResearchQueryInputSchema,
  InsightExtractionInputSchema,
  LinkedInPostInputSchema,
  ContentWorkflowInputSchema,
} from '../types/schemas.js';

export async function agentRoutes(fastify: FastifyInstance) {
  // Generic agent run endpoint
  fastify.post('/agent/run', {
    schema: {
      description: 'Run an agent with specified type and input',
      tags: ['Agents'],
      body: {
        type: 'object',
        required: ['agentType', 'input'],
        properties: {
          agentType: {
            type: 'string',
            enum: Object.values(AgentType),
            description: 'Type of agent to run'
          },
          input: {
            type: 'object',
            additionalProperties: true,
            description: 'Agent-specific input parameters'
          }
        }
      },
      response: {
        200: {
          description: 'Agent job submitted successfully',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  jobId: { type: 'string' },
                  agentType: { type: 'string' },
                  message: { type: 'string' }
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
                  success: { type: 'boolean' },
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
        const { agentType, input } = request.body as { agentType: AgentType; input: Record<string, unknown> };
        const result = await submitAgentJob(agentType, input);
        return reply.send(result);
      } catch (error: any) {
        return reply.code(400).send({ success: false, error: error.message });
      }
    }
  });

  // Research Query Agent endpoint
  fastify.post('/agent/research-query', {
    schema: {
      description: 'Run the Research Query Agent for hybrid RAG search',
      tags: ['Agents'],
      body: {
        type: 'object',
        required: ['query'],
        properties: {
          query: { type: 'string', minLength: 1, description: 'Search query' },
          maxResults: { type: 'number', minimum: 1, maximum: 50, default: 10 },
          minScore: { type: 'number', minimum: 0, maximum: 1, default: 0.01 },
          includeContext: { type: 'boolean', default: true }
        }
      },
      response: {
        200: {
          description: 'Agent job submitted successfully',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  jobId: { type: 'string' },
                  agentType: { type: 'string' },
                  message: { type: 'string' }
                }
              }
            }
          }
        }
      }
    },
    handler: async (request, reply) => {
      try {
        const input = ResearchQueryInputSchema.parse(request.body);
        const result = await submitResearchQueryJob(input);
        return reply.send(result);
      } catch (error: any) {
        return reply.code(400).send({ success: false, error: error.message });
      }
    }
  });

  // Insight Extraction Agent endpoint
  fastify.post('/agent/insight-extraction', {
    schema: {
      description: 'Run the Insight Extraction Agent to extract structured insights',
      tags: ['Agents'],
      body: {
        type: 'object',
        required: ['query'],
        properties: {
          query: { type: 'string', minLength: 1, description: 'Topic or query for insight extraction' },
          maxResults: { type: 'number', minimum: 1, maximum: 20, default: 5 },
          minScore: { type: 'number', minimum: 0, maximum: 1, default: 0.3 }
        }
      },
      response: {
        200: {
          description: 'Agent job submitted successfully',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  jobId: { type: 'string' },
                  agentType: { type: 'string' },
                  message: { type: 'string' }
                }
              }
            }
          }
        }
      }
    },
    handler: async (request, reply) => {
      try {
        const input = InsightExtractionInputSchema.parse(request.body);
        const result = await submitInsightExtractionJob(input);
        return reply.send(result);
      } catch (error: any) {
        return reply.code(400).send({ success: false, error: error.message });
      }
    }
  });

  // LinkedIn Post Generator Agent endpoint
  fastify.post('/agent/linkedin-post', {
    schema: {
      description: 'Run the LinkedIn Post Generator Agent',
      tags: ['Agents'],
      body: {
        type: 'object',
        required: ['insights'],
        properties: {
          title: { type: 'string', description: 'Optional post title' },
          insights: {
            type: 'array',
            items: {
              type: 'object',
              required: ['claim'],
              properties: {
                claim: { type: 'string' },
                confidence: { type: 'number' },
                evidence: {
                  type: 'array',
                  items: {
                    type: 'object',
                    properties: {
                      excerpt: { type: 'string' },
                      documentId: { type: 'string' },
                      chunkIndex: { type: 'number' }
                    }
                  }
                }
              }
            },
            description: 'Insights to include in the post'
          },
          tone: { type: 'string', enum: ['professional', 'casual', 'thought-leadership'], default: 'professional' },
          maxLength: { type: 'number', minimum: 100, maximum: 3000, default: 700 }
        }
      },
      response: {
        200: {
          description: 'Agent job submitted successfully',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  jobId: { type: 'string' },
                  agentType: { type: 'string' },
                  message: { type: 'string' }
                }
              }
            }
          }
        }
      }
    },
    handler: async (request, reply) => {
      try {
        const input = LinkedInPostInputSchema.parse(request.body);
        const result = await submitLinkedInPostJob(input);
        return reply.send(result);
      } catch (error: any) {
        return reply.code(400).send({ success: false, error: error.message });
      }
    }
  });

  // Content Workflow Agent endpoint (Combined Phase 4+5)
  fastify.post('/agent/content-workflow', {
    schema: {
      description: 'Run the full Content Workflow: Research Query -> Insight Extraction -> LinkedIn Post Generation',
      tags: ['Agents'],
      body: {
        type: 'object',
        required: ['query'],
        properties: {
          query: { type: 'string', minLength: 1, description: 'Research topic or question' },
          maxResults: { type: 'number', minimum: 1, maximum: 20, default: 5 },
          tone: { type: 'string', enum: ['professional', 'casual', 'thought-leadership'], default: 'professional' },
          maxPostLength: { type: 'number', minimum: 100, maximum: 3000, default: 700 }
        }
      },
      response: {
        200: {
          description: 'Agent job submitted successfully',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  success: { type: 'boolean' },
                  jobId: { type: 'string' },
                  agentType: { type: 'string' },
                  message: { type: 'string' }
                }
              }
            }
          }
        }
      }
    },
    handler: async (request, reply) => {
      try {
        const input = ContentWorkflowInputSchema.parse(request.body);
        const result = await submitContentWorkflowJob(input);
        return reply.send(result);
      } catch (error: any) {
        return reply.code(400).send({ success: false, error: error.message });
      }
    }
  });
}
