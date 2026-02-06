import { z } from 'zod';

// Job Status Enum
export enum JobStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  SUCCESS = 'success',
  FAILED = 'failed'
}

// Project Document Status Enum
export enum ProjectDocumentStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

// Document Schemas
export const DocumentSchema = z.object({
  id: z.string().uuid(),
  title: z.string(),
  source_url: z.string().nullable(),
  file_type: z.string().nullable(),
  file_size: z.number().nullable(),
  blob_reference: z.string().nullable(),
  checksum: z.string().nullable(),
  metadata: z.record(z.unknown()),
  parsing_attempts: z.number(),
  parsing_failures: z.number(),
  last_parsing_error: z.string().nullable(),
  last_parsing_attempt_at: z.date().nullable(),
  parsing_blocked: z.boolean(),
  created_at: z.date(),
  updated_at: z.date()
});

export const CreateDocumentSchema = z.object({
  title: z.string(),
  source_url: z.string().url().optional(),
  file_type: z.string().optional(),
  file_size: z.number().optional(),
  blob_reference: z.string().optional(),
  checksum: z.string().optional(),
  metadata: z.record(z.unknown()).optional()
});

// Project Schemas
export const ProjectSchema = z.object({
  id: z.string().uuid(),
  key: z.string(),
  name: z.string(),
  description: z.string().nullable(),
  settings: z.record(z.unknown()),
  created_at: z.date(),
  updated_at: z.date()
});

// Project Document Schemas
export const ProjectDocumentSchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  document_id: z.string().uuid(),
  status: z.nativeEnum(ProjectDocumentStatus),
  project_metadata: z.record(z.unknown()),
  error_message: z.string().nullable(),
  added_at: z.date(),
  processed_at: z.date().nullable()
});

// Vector Schemas
export const DocumentVectorSchema = z.object({
  id: z.string().uuid(),
  project_document_id: z.string().uuid(),
  chunk_index: z.number(),
  content: z.string(),
  context_summary: z.string().nullable(),
  token_count: z.number().nullable(),
  metadata: z.record(z.unknown()),
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
  project_key: z.string().default('researchpaper'),
  metadata: z.record(z.unknown()).optional()
});

export const ProcessPdfRequestSchema = z.object({
  url: z.string().url().describe('URL of the PDF to process'),
  title: z.string().optional().describe('Optional title for the document'),
  project_key: z.string().optional().default('researchpaper').describe('Project key (defaults to researchpaper)'),
  metadata: z.record(z.unknown()).optional().describe('Optional metadata')
});

// Query Schemas
export const QueryRequestSchema = z.object({
  query: z.string().min(1).describe('Search query'),
  limit: z.number().min(1).max(100).default(10).optional().describe('Number of results'),
  project_key: z.string().optional().default('researchpaper').describe('Project key to search within'),
  document_id: z.string().uuid().optional().describe('Filter by specific document')
});

export const QueryResultSchema = z.object({
  content: z.string(),
  context_summary: z.string().nullable(),
  similarity: z.number(),
  document_id: z.string().uuid(),
  document_title: z.string().optional(),
  chunk_index: z.number(),
  metadata: z.record(z.unknown()).optional()
});

export const QueryResponseSchema = z.object({
  results: z.array(QueryResultSchema),
  query: z.string(),
  project_key: z.string(),
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
export type Project = z.infer<typeof ProjectSchema>;
export type ProjectDocument = z.infer<typeof ProjectDocumentSchema>;
export type DocumentVector = z.infer<typeof DocumentVectorSchema>;
export type JobResponse = z.infer<typeof JobResponseSchema>;
export type JobStatusResponse = z.infer<typeof JobStatusResponseSchema>;
export type ProcessPdfJobData = z.infer<typeof ProcessPdfJobDataSchema>;
export type ProcessPdfRequest = z.infer<typeof ProcessPdfRequestSchema>;
export type QueryRequest = z.infer<typeof QueryRequestSchema>;
export type QueryResult = z.infer<typeof QueryResultSchema>;
export type QueryResponse = z.infer<typeof QueryResponseSchema>;
export type HealthCheck = z.infer<typeof HealthCheckSchema>;
