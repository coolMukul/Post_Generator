import { Job } from 'bullmq';
import { pdfProcessingQueue } from '../config/queue.js';
import { JobStatus, JobStatusResponse } from '../types/schemas.js';

export const getJobStatus = async (jobId: string): Promise<JobStatusResponse> => {
  const job = await pdfProcessingQueue.getJob(jobId);

  if (!job) {
    throw new Error('Job not found');
  }

  const state = await job.getState();
  let status: JobStatus;

  switch (state) {
    case 'completed':
      status = JobStatus.SUCCESS;
      break;
    case 'failed':
      status = JobStatus.FAILED;
      break;
    case 'active':
      status = JobStatus.IN_PROGRESS;
      break;
    default:
      status = JobStatus.PENDING;
  }

  const progress = job.progress as number | undefined;

  return {
    job_id: job.id!,
    status,
    created_at: new Date(job.timestamp),
    started_at: job.processedOn ? new Date(job.processedOn) : null,
    completed_at: job.finishedOn ? new Date(job.finishedOn) : null,
    result: job.returnvalue || null,
    error: job.failedReason || null,
    progress: progress || 0,
  };
};

export const listJobs = async (status?: JobStatus, limit = 50): Promise<JobStatusResponse[]> => {
  let jobs: Job[] = [];

  switch (status) {
    case JobStatus.SUCCESS:
      jobs = await pdfProcessingQueue.getCompleted(0, limit - 1);
      break;
    case JobStatus.FAILED:
      jobs = await pdfProcessingQueue.getFailed(0, limit - 1);
      break;
    case JobStatus.IN_PROGRESS:
      jobs = await pdfProcessingQueue.getActive(0, limit - 1);
      break;
    case JobStatus.PENDING:
      jobs = await pdfProcessingQueue.getWaiting(0, limit - 1);
      break;
    default:
      // Get all jobs
      const [completed, failed, active, waiting] = await Promise.all([
        pdfProcessingQueue.getCompleted(0, Math.floor(limit / 4)),
        pdfProcessingQueue.getFailed(0, Math.floor(limit / 4)),
        pdfProcessingQueue.getActive(0, Math.floor(limit / 4)),
        pdfProcessingQueue.getWaiting(0, Math.floor(limit / 4)),
      ]);
      jobs = [...completed, ...failed, ...active, ...waiting];
  }

  return Promise.all(jobs.map(async (job) => {
    const state = await job.getState();
    let jobStatus: JobStatus;

    switch (state) {
      case 'completed':
        jobStatus = JobStatus.SUCCESS;
        break;
      case 'failed':
        jobStatus = JobStatus.FAILED;
        break;
      case 'active':
        jobStatus = JobStatus.IN_PROGRESS;
        break;
      default:
        jobStatus = JobStatus.PENDING;
    }

    return {
      job_id: job.id!,
      status: jobStatus,
      created_at: new Date(job.timestamp),
      started_at: job.processedOn ? new Date(job.processedOn) : null,
      completed_at: job.finishedOn ? new Date(job.finishedOn) : null,
      result: job.returnvalue || null,
      error: job.failedReason || null,
      progress: (job.progress as number) || 0,
    };
  }));
};
