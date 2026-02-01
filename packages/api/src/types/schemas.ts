import { z } from 'zod';

// Job Status Enum
export enum JobStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  SUCCESS = 'success',
  FAILED = 'failed'
}

// Document Schemas
export const DocumentSchema = z.object({
  id: z.number(),
  url: z.string().url(),
  title: z.string().nullable(),
  checksum: z.string(),
  metadata: z.record(z.unknown()).optional(),
  created_at: z.date()
});

export const CreateDocumentSchema = z.object({
  url: z.string().url(),
  title: z.string().optional(),
  metadata: z.record(z.unknown()).optional()
});

// Vector Schemas
export const VectorSchema = z.object({
  id: z.number(),
  document_id: z.number(),
  chunk_index: z.number(),
  content: z.string(),
  context_summary: z.string().nullable(),
  token_count: z.number().nullable(),
  created_at: z.date()
});

// Job Schemas
export const JobResponseSchema = z.object({
  job_id: z.string(),
  status: z.nativeEnum(JobStatus),
  created_at: z.date(),
  message: z.string().optional()
});

export const JobStatusResponseSchema = z.object({
  job_id: z.string(),
  status: z.nativeEnum(JobStatus),
  created_at: z.date(),
  started_at: z.date().nullable(),
  completed_at: z.date().nullable(),
  result: z.unknown().nullable(),
  error: z.string().nullable(),
  progress: z.number().min(0).max(100).optional()
});

// PDF Processing Job
export const ProcessPdfJobDataSchema = z.object({
  url: z.string().url(),
  title: z.string().optional(),
  metadata: z.record(z.unknown()).optional()
});

export const ProcessPdfRequestSchema = z.object({
  url: z.string().url().describe('URL of the PDF to process'),
  title: z.string().optional().describe('Optional title for the document'),
  metadata: z.record(z.unknown()).optional().describe('Optional metadata')
});

// Query Schemas
export const QueryRequestSchema = z.object({
  query: z.string().min(1).describe('Search query'),
  limit: z.number().min(1).max(100).default(10).optional().describe('Number of results'),
  document_id: z.number().optional().describe('Filter by specific document')
});

export const QueryResultSchema = z.object({
  content: z.string(),
  context_summary: z.string().nullable(),
  similarity: z.number(),
  document_id: z.number(),
  chunk_index: z.number()
});

export const QueryResponseSchema = z.object({
  results: z.array(QueryResultSchema),
  query: z.string(),
  total: z.number()
});

// Health Check Schema
export const HealthCheckSchema = z.object({
  status: z.enum(['healthy', 'unhealthy']),
  timestamp: z.string(),
  services: z.object({
    database: z.boolean(),
    redis: z.boolean()
  })
});

// TypeScript Types
export type Document = z.infer<typeof DocumentSchema>;
export type CreateDocument = z.infer<typeof CreateDocumentSchema>;
export type Vector = z.infer<typeof VectorSchema>;
export type JobResponse = z.infer<typeof JobResponseSchema>;
export type JobStatusResponse = z.infer<typeof JobStatusResponseSchema>;
export type ProcessPdfJobData = z.infer<typeof ProcessPdfJobDataSchema>;
export type ProcessPdfRequest = z.infer<typeof ProcessPdfRequestSchema>;
export type QueryRequest = z.infer<typeof QueryRequestSchema>;
export type QueryResult = z.infer<typeof QueryResultSchema>;
export type QueryResponse = z.infer<typeof QueryResponseSchema>;
export type HealthCheck = z.infer<typeof HealthCheckSchema>;
