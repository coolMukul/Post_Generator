import { pdfProcessingQueue } from '../config/queue.js';
import { ProcessPdfJobData, JobResponse, JobStatus } from '../types/schemas.js';

export const submitPdfProcessingJob = async (data: ProcessPdfJobData): Promise<JobResponse> => {
  const job = await pdfProcessingQueue.add('process-pdf', data, {
    jobId: `pdf-${Date.now()}-${Math.random().toString(36).substring(7)}`,
  });

  return {
    job_id: job.id!,
    status: JobStatus.PENDING,
    created_at: new Date(job.timestamp),
    message: 'PDF processing job submitted successfully',
  };
};
