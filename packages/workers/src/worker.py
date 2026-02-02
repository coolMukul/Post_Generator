"""BullMQ worker for processing jobs."""
import asyncio
import logging
import json
from redis import asyncio as aioredis
from .config import settings, get_redis_url
from .jobs import process_pdf_job

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BullMQWorker:
    """Simple BullMQ worker that consumes jobs from Redis."""

    def __init__(self, queue_name: str, redis_url: str, concurrency: int = 1):
        self.queue_name = queue_name
        self.redis_url = redis_url
        self.concurrency = concurrency
        self.redis = None
        self.running = False

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

            logger.info(f"Processing job: {job_id}")
            logger.info(f"Job data: {data}")

            # Process the PDF job
            result = await process_pdf_job(job_id, data)

            logger.info(f"Job {job_id} completed successfully")
            return result

        except Exception as e:
            logger.error(f"Job processing failed: {str(e)}", exc_info=True)
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
                    job_data_str = await self.redis.get(job_key)

                    if job_data_str:
                        job_data = json.loads(job_data_str)
                        await self.process_job(job_data)
                else:
                    # No jobs available, wait a bit
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error polling jobs: {str(e)}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying

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
    logger.info("Starting PDF Processing Worker")
    logger.info("="*60)
    logger.info(f"Redis URL: {get_redis_url()}")
    logger.info(f"Queue: pdf-processing")
    logger.info(f"Concurrency: {settings.worker_concurrency}")
    logger.info("="*60)

    # Create and start worker
    worker = BullMQWorker(
        queue_name="pdf-processing",
        redis_url=get_redis_url(),
        concurrency=settings.worker_concurrency
    )

    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("\nReceived shutdown signal")
        await worker.stop()
    except Exception as e:
        logger.error(f"Worker error: {str(e)}", exc_info=True)
        await worker.stop()
        raise


if __name__ == "__main__":
    asyncio.run(main())
