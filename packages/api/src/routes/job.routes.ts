import { FastifyInstance } from 'fastify';
import { getJobStatus, getJobStatusForUI, listJobs } from '../handlers/job.handler.js';
import { JobStatus } from '../types/schemas.js';

// Schema for job status response
const jobStatusSchema = {
  description: 'Get job status by ID',
  tags: ['Jobs'],
  params: {
    type: 'object',
    properties: {
      jobId: { type: 'string', description: 'Job ID' }
    },
    required: ['jobId']
  },
  response: {
    200: {
      description: 'Job status',
      content: {
        'application/json': {
          schema: {
            type: 'object',
            properties: {
              job_id: { type: 'string' },
              status: { type: 'string', enum: Object.values(JobStatus) },
              state: { type: 'string' },
              created_at: { type: 'string' },
              started_at: { type: 'string', nullable: true },
              completed_at: { type: 'string', nullable: true },
              result: { nullable: true },
              returnvalue: { nullable: true },
              error: { type: 'string', nullable: true },
              failedReason: { type: 'string', nullable: true },
              progress: { type: 'number' }
            }
          }
        }
      }
    },
    404: {
      description: 'Job not found',
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
};

export async function jobRoutes(fastify: FastifyInstance) {
  // Original route: /jobs/:jobId
  fastify.get('/jobs/:jobId', {
    schema: jobStatusSchema,
    handler: async (request, reply) => {
      try {
        const { jobId } = request.params as { jobId: string };
        const status = await getJobStatus(jobId);
        return reply.send(status);
      } catch (error: any) {
        return reply.code(404).send({ error: error.message });
      }
    }
  });

  // Alias route: /queue/jobs/:jobId (used by UI for polling)
  fastify.get('/queue/jobs/:jobId', {
    schema: { ...jobStatusSchema, description: 'Get job status by ID (alias for UI polling)' },
    handler: async (request, reply) => {
      try {
        const { jobId } = request.params as { jobId: string };
        // Use the UI-friendly format with BullMQ-style fields
        const status = await getJobStatusForUI(jobId);
        return reply.send(status);
      } catch (error: any) {
        return reply.code(404).send({ error: error.message });
      }
    }
  });

  fastify.get('/jobs', {
    schema: {
      description: 'List jobs with optional status filter',
      tags: ['Jobs'],
      querystring: {
        type: 'object',
        properties: {
          status: {
            type: 'string',
            enum: Object.values(JobStatus),
            description: 'Filter by job status'
          },
          limit: {
            type: 'number',
            minimum: 1,
            maximum: 100,
            default: 50,
            description: 'Maximum number of jobs to return'
          }
        }
      },
      response: {
        200: {
          description: 'List of jobs',
          content: {
            'application/json': {
              schema: {
                type: 'array',
                items: {
                  type: 'object',
                  properties: {
                    job_id: { type: 'string' },
                    status: { type: 'string', enum: Object.values(JobStatus) },
                    created_at: { type: 'string' },
                    started_at: { type: 'string', nullable: true },
                    completed_at: { type: 'string', nullable: true },
                    result: { nullable: true },
                    error: { type: 'string', nullable: true },
                    progress: { type: 'number' }
                  }
                }
              }
            }
          }
        }
      }
    },
    handler: async (request, reply) => {
      const { status, limit = 50 } = request.query as { status?: JobStatus; limit?: number };
      const jobs = await listJobs(status, limit);
      return reply.send(jobs);
    }
  });
}
