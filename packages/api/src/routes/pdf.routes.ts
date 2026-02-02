import { FastifyInstance } from 'fastify';
import { submitPdfProcessingJob } from '../handlers/pdf.handler.js';
import { ProcessPdfRequestSchema, JobStatus } from '../types/schemas.js';

export async function pdfRoutes(fastify: FastifyInstance) {
  fastify.post('/pdf/process', {
    schema: {
      description: 'Submit a PDF for processing',
      tags: ['PDF'],
      body: {
        type: 'object',
        required: ['url'],
        properties: {
          url: { type: 'string', format: 'uri', description: 'URL of the PDF to process' },
          title: { type: 'string', description: 'Optional title for the document' },
          metadata: {
            type: 'object',
            additionalProperties: true,
            description: 'Optional metadata'
          }
        }
      },
      response: {
        200: {
          description: 'Job submitted successfully',
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  job_id: { type: 'string' },
                  status: { type: 'string', enum: Object.values(JobStatus) },
                  created_at: { type: 'string' },
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
        const data = ProcessPdfRequestSchema.parse(request.body);
        const result = await submitPdfProcessingJob(data);
        return reply.send(result);
      } catch (error: any) {
        return reply.code(400).send({ error: error.message });
      }
    }
  });
}
