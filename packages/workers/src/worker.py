"""BullMQ worker for processing jobs."""
import asyncio
import logging
import json
from redis import asyncio as aioredis
from .config import settings, get_redis_url
from .jobs import process_pdf_job
from .jobs.agent_processor import process_agent_job

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BullMQWorker:
    """Simple BullMQ worker that consumes jobs from Redis."""

    def __init__(self, queue_name: str, redis_url: str, concurrency: int = 1, job_type: str = 'pdf'):
        self.queue_name = queue_name
        self.redis_url = redis_url
        self.concurrency = concurrency
        self.redis = None
        self.running = False
        self.job_type = job_type  # 'pdf' or 'agent'

    async def connect(self):
        """Connect to Redis."""
        self.redis = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info(f"Connected to Redis: {self.redis_url}")

    async def process_job(self, job_data: dict):
        """
        Process a single job.

        Args:
            job_data: Job data from BullMQ
        """
        try:
            job_id = job_data.get('id', 'unknown')
            data = job_data.get('data', {})

            logger.info(f"[{self.job_type}] Processing job: {job_id}")
            logger.info(f"[{self.job_type}] Job data: {data}")

            if self.job_type == 'agent':
                # Process agent job
                result = await process_agent_job(job_id, data)
            else:
                # Process the PDF job
                result = await process_pdf_job(job_id, data)

            logger.info(f"[{self.job_type}] Job {job_id} completed successfully")
            return result

        except Exception as e:
            logger.error(f"[{self.job_type}] Job processing failed: {str(e)}", exc_info=True)
            raise

    async def poll_jobs(self):
        """
        Poll for jobs from BullMQ queue.

        Note: This is a simplified implementation. For production, you would:
        1. Use BRPOPLPUSH for atomic job retrieval
        2. Handle job acknowledgment properly
        3. Implement retry logic
        4. Update job status in Redis
        """
        logger.info(f"Polling for jobs from queue: {self.queue_name}")

        while self.running:
            try:
                # BullMQ stores jobs in Redis lists with specific keys
                # Format: bull:{queue_name}:wait
                wait_key = f"bull:{self.queue_name}:wait"

                # Try to get a job (non-blocking check)
                job_id = await self.redis.lpop(wait_key)

                if job_id:
                    # Get job data
                    job_key = f"bull:{self.queue_name}:{job_id}"
                    try:
                        key_type = await self.redis.type(job_key)
                    except Exception as e:
                        logger.error(f"Failed to get key type for {job_key}: {e}")
                        await asyncio.sleep(1)
                        continue

                    job_data_str = None
                    if key_type == 'string':
                        job_data_str = await self.redis.get(job_key)
                    elif key_type == 'hash':
                        # Bull stores job data in a hash; try common fields
                        job_hash = await self.redis.hgetall(job_key)
                        # Look for a field that likely contains JSON payload
                        for candidate in ('data', 'json', 'payload', 'value'):
                            if candidate in job_hash and job_hash[candidate]:
                                job_data_str = job_hash[candidate]
                                break
                        # Fallback: if single-field hash, use its value
                        if not job_data_str and len(job_hash) == 1:
                            job_data_str = next(iter(job_hash.values()))
                    elif key_type in ('list', 'set'):
                        # If key holds a list/set, try to read the first element
                        items = await self.redis.lrange(job_key, 0, 0) if key_type == 'list' else await self.redis.smembers(job_key)
                        if items:
                            # items may be a list or set; take first element
                            job_data_str = items[0] if isinstance(items, list) else next(iter(items))
                    else:
                        logger.error(f"Unsupported Redis key type for job key {job_key}: {key_type}")

                    if job_data_str:
                        try:
                            parsed = json.loads(job_data_str)
                        except Exception:
                            parsed = job_data_str if isinstance(job_data_str, dict) else job_data_str

                        # If parsed is the raw payload (contains 'url'), wrap into job object
                        if isinstance(parsed, dict) and parsed.get('url'):
                            job_obj = {'id': job_id, 'data': parsed}
                        else:
                            job_obj = parsed

                        # Validate required field before processing
                        if self.job_type == 'agent':
                            # Agent jobs need agentType and input
                            if not job_obj or not (isinstance(job_obj, dict) and job_obj.get('data') and job_obj['data'].get('agentType')):
                                logger.error('Agent job payload missing `agentType`. job_key=%s job_data_preview=%s', job_key, str(parsed)[:200])
                            else:
                                result = await self.process_job(job_obj)
                                # Store result in Redis for the API to retrieve
                                await self.store_job_result(job_id, result)
                        else:
                            # PDF jobs need url
                            if not job_obj or not (isinstance(job_obj, dict) and job_obj.get('data') and job_obj['data'].get('url')):
                                logger.error('Job payload missing `url`. job_key=%s job_data_preview=%s', job_key, str(parsed)[:200])
                            else:
                                await self.process_job(job_obj)
                else:
                    # No jobs available, wait a bit
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error polling jobs: {str(e)}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying

    async def store_job_result(self, job_id: str, result: dict):
        """Store job result in Redis for BullMQ to retrieve."""
        try:
            job_key = f"bull:{self.queue_name}:{job_id}"

            # BullMQ expects returnvalue to be stored
            # Update the job hash with the result
            await self.redis.hset(job_key, mapping={
                'returnvalue': json.dumps(result),
                'finishedOn': str(int(asyncio.get_event_loop().time() * 1000)),
                'processedOn': str(int(asyncio.get_event_loop().time() * 1000)),
            })

            # Move job from active to completed
            active_key = f"bull:{self.queue_name}:active"
            completed_key = f"bull:{self.queue_name}:completed"

            # Remove from active and add to completed
            await self.redis.lrem(active_key, 1, job_id)
            await self.redis.lpush(completed_key, job_id)

            logger.info(f"[{self.job_type}] Job {job_id} result stored and marked as completed")
        except Exception as e:
            logger.error(f"[{self.job_type}] Failed to store job result: {str(e)}", exc_info=True)

    async def start(self):
        """Start the worker."""
        self.running = True
        await self.connect()

        # Create multiple worker tasks based on concurrency
        tasks = []
        for i in range(self.concurrency):
            task = asyncio.create_task(self.poll_jobs())
            tasks.append(task)
            logger.info(f"Started worker {i+1}/{self.concurrency}")

        # Wait for all tasks
        await asyncio.gather(*tasks)

    async def stop(self):
        """Stop the worker."""
        logger.info("Stopping worker...")
        self.running = False
        if self.redis:
            await self.redis.close()


async def main():
    """Main worker loop."""
    logger.info("="*60)
    logger.info("Starting Workers (PDF + Agent)")
    logger.info("="*60)
    logger.info(f"Redis URL: {get_redis_url()}")
    logger.info(f"Queues: pdf-processing, agent-tasks")
    logger.info(f"Concurrency: {settings.worker_concurrency}")
    logger.info("="*60)

    # Create workers for both queues
    pdf_worker = BullMQWorker(
        queue_name="pdf-processing",
        redis_url=get_redis_url(),
        concurrency=settings.worker_concurrency,
        job_type='pdf'
    )

    agent_worker = BullMQWorker(
        queue_name="agent-tasks",
        redis_url=get_redis_url(),
        concurrency=settings.worker_concurrency,
        job_type='agent'
    )

    try:
        # Run both workers concurrently
        await asyncio.gather(
            pdf_worker.start(),
            agent_worker.start()
        )
    except KeyboardInterrupt:
        logger.info("\nReceived shutdown signal")
        await pdf_worker.stop()
        await agent_worker.stop()
    except Exception as e:
        logger.error(f"Worker error: {str(e)}", exc_info=True)
        await pdf_worker.stop()
        await agent_worker.stop()
        raise


if __name__ == "__main__":
    asyncio.run(main())
