import { Job } from 'bullmq';
import { pdfProcessingQueue, agentTasksQueue, redisClient, QUEUE_NAMES } from '../config/queue.js';
import { JobStatus, JobStatusResponse } from '../types/schemas.js';

// Helper to get job from any queue
async function getJobFromQueues(jobId: string): Promise<Job | null> {
  // Try PDF processing queue first
  let job = await pdfProcessingQueue.getJob(jobId);
  if (job) return job;

  // Try agent tasks queue
  job = await agentTasksQueue.getJob(jobId);
  if (job) return job;

  return null;
}

// Direct Redis lookup for job data (fallback when BullMQ getJob fails)
interface RedisJobData {
  jobId: string;
  queueName: string;
  state: 'waiting' | 'active' | 'completed' | 'failed' | 'delayed';
  data: Record<string, unknown> | null;
  returnvalue: unknown | null;
  failedReason: string | null;
  timestamp: number;
  processedOn: number | null;
  finishedOn: number | null;
  progress: number;
}

async function getJobFromRedis(jobId: string): Promise<RedisJobData | null> {
  // Try to find job in different queues
  const queues = [QUEUE_NAMES.AGENT_TASKS, QUEUE_NAMES.PDF_PROCESSING];

  for (const queueName of queues) {
    const jobKey = `bull:${queueName}:${jobId}`;

    // Check if job hash exists
    const exists = await redisClient.exists(jobKey);
    if (!exists) continue;

    // Get job data from hash
    const jobHash = await redisClient.hgetall(jobKey);
    if (!jobHash || Object.keys(jobHash).length === 0) continue;

    // Determine state by checking job hash fields first (more reliable)
    // BullMQ uses sorted sets for completed/failed, lists for wait/active
    let state: RedisJobData['state'] = 'waiting';

    // First, check hash fields - most reliable for completed jobs
    if (jobHash.finishedOn && jobHash.returnvalue) {
      state = 'completed';
    } else if (jobHash.finishedOn && jobHash.failedReason) {
      state = 'failed';
    } else {
      // Check lists for wait/active states (these are actual lists)
      try {
        const inActive = await redisClient.lpos(`bull:${queueName}:active`, jobId);
        if (inActive !== null) {
          state = 'active';
        } else {
          const inWait = await redisClient.lpos(`bull:${queueName}:wait`, jobId);
          if (inWait !== null) {
            state = 'waiting';
          }
        }
      } catch {
        // If lpos fails (WRONGTYPE), fall back to checking sorted sets
        try {
          // BullMQ uses sorted sets for completed/failed
          const completedScore = await redisClient.zscore(`bull:${queueName}:completed`, jobId);
          if (completedScore !== null) {
            state = 'completed';
          } else {
            const failedScore = await redisClient.zscore(`bull:${queueName}:failed`, jobId);
            if (failedScore !== null) {
              state = 'failed';
            }
          }
        } catch {
          // If all else fails, use hash fields or default to waiting
          if (jobHash.processedOn && !jobHash.finishedOn) {
            state = 'active';
          }
        }
      }
    }

    // Parse job data
    let data: Record<string, unknown> | null = null;
    if (jobHash.data) {
      try {
        data = JSON.parse(jobHash.data);
      } catch {
        data = null;
      }
    }

    // Parse returnvalue
    let returnvalue: unknown | null = null;
    if (jobHash.returnvalue) {
      try {
        returnvalue = JSON.parse(jobHash.returnvalue);
      } catch {
        returnvalue = jobHash.returnvalue;
      }
    }

    return {
      jobId,
      queueName,
      state,
      data,
      returnvalue,
      failedReason: jobHash.failedReason || null,
      timestamp: parseInt(jobHash.timestamp || '0', 10),
      processedOn: jobHash.processedOn ? parseInt(jobHash.processedOn, 10) : null,
      finishedOn: jobHash.finishedOn ? parseInt(jobHash.finishedOn, 10) : null,
      progress: parseInt(jobHash.progress || '0', 10),
    };
  }

  return null;
}

export const getJobStatus = async (jobId: string): Promise<JobStatusResponse> => {
  const job = await getJobFromQueues(jobId);

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

// UI-friendly job status with BullMQ-style field names
export interface JobStatusForUI {
  job_id: string;
  state: 'completed' | 'failed' | 'active' | 'waiting' | 'delayed';
  returnvalue: unknown | null;
  failedReason: string | null;
  progress: number;
  timestamp: number;
  processedOn: number | null;
  finishedOn: number | null;
}

export const getJobStatusForUI = async (jobId: string): Promise<JobStatusForUI> => {
  // Try BullMQ first
  const job = await getJobFromQueues(jobId);

  if (job) {
    const state = await job.getState();
    return {
      job_id: job.id!,
      state: state as JobStatusForUI['state'],
      returnvalue: job.returnvalue || null,
      failedReason: job.failedReason || null,
      progress: (job.progress as number) || 0,
      timestamp: job.timestamp,
      processedOn: job.processedOn || null,
      finishedOn: job.finishedOn || null,
    };
  }

  // Fallback: direct Redis lookup
  const redisJob = await getJobFromRedis(jobId);

  if (redisJob) {
    return {
      job_id: redisJob.jobId,
      state: redisJob.state,
      returnvalue: redisJob.returnvalue,
      failedReason: redisJob.failedReason,
      progress: redisJob.progress,
      timestamp: redisJob.timestamp,
      processedOn: redisJob.processedOn,
      finishedOn: redisJob.finishedOn,
    };
  }

  throw new Error('Job not found');
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
