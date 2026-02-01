"""BullMQ worker for processing jobs."""
import asyncio
import logging
from python_bullmq import Worker, Job
from .config import settings, get_redis_url
from .jobs import process_pdf_job

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def pdf_processing_handler(job: Job, job_token: str) -> dict:
    """
    Handler for PDF processing jobs.

    Args:
        job: BullMQ job instance
        job_token: Job token for updates

    Returns:
        Job result dictionary
    """
    try:
        logger.info(f"Processing job: {job.id}")

        # Update job progress
        await job.update_progress(10)

        # Process the job
        result = await process_pdf_job(job.id, job.data)

        # Update job progress
        await job.update_progress(100)

        return result

    except Exception as e:
        logger.error(f"Job {job.id} failed: {str(e)}", exc_info=True)
        raise


async def main():
    """Main worker loop."""
    logger.info("Starting PDF processing worker")
    logger.info(f"Redis URL: {get_redis_url()}")
    logger.info(f"Concurrency: {settings.worker_concurrency}")

    # Create worker for PDF processing queue
    worker = Worker(
        "pdf-processing",
        pdf_processing_handler,
        {
            "connection": get_redis_url(),
            "concurrency": settings.worker_concurrency,
            "autorun": False
        }
    )

    logger.info("Worker initialized, starting to process jobs...")

    try:
        # Run the worker
        await worker.run()

        # Keep the worker running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down worker...")
        await worker.close()
    except Exception as e:
        logger.error(f"Worker error: {str(e)}", exc_info=True)
        await worker.close()
        raise


if __name__ == "__main__":
    asyncio.run(main())
