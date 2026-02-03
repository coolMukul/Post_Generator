import { Job } from 'bullmq';
import { mainProcessingQueue } from '../config/queue.js';
import { JobStatus, JobStatusResponse } from '../types/schemas.js';

export const getJobStatus = async (jobId: string): Promise<JobStatusResponse> => {
  const job = await mainProcessingQueue.getJob(jobId);

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
      jobs = await mainProcessingQueue.getCompleted(0, limit - 1);
      break;
    case JobStatus.FAILED:
      jobs = await mainProcessingQueue.getFailed(0, limit - 1);
      break;
    case JobStatus.IN_PROGRESS:
      jobs = await mainProcessingQueue.getActive(0, limit - 1);
      break;
    case JobStatus.PENDING:
      jobs = await mainProcessingQueue.getWaiting(0, limit - 1);
      break;
    default:
      // Get all jobs
      const [completed, failed, active, waiting] = await Promise.all([
        mainProcessingQueue.getCompleted(0, Math.floor(limit / 4)),
        mainProcessingQueue.getFailed(0, Math.floor(limit / 4)),
        mainProcessingQueue.getActive(0, Math.floor(limit / 4)),
        mainProcessingQueue.getWaiting(0, Math.floor(limit / 4)),
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
