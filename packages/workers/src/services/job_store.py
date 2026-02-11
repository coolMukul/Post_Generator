"""Redis-backed job store for background job lifecycle management.

Job statuses per CodingGuidelines.md:
  - InProgress: with start_time
  - Success: with result (JSON), start_time, end_time
  - Failed: with error message, start_time, end_time
"""
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis

from ..config import get_redis_url
from ..models.schemas import JobStatus

logger = logging.getLogger(__name__)

JOB_KEY_PREFIX = "job:"
QUEUE_KEY = "main_queue"
JOB_TTL_SECONDS = 3600  # keep finished jobs for 1 hour


class JobStore:
    """Thin wrapper around Redis for job CRUD and the main work queue."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis = redis.Redis.from_url(redis_url or get_redis_url(), decode_responses=True)

    def create_job(self, job_type: str, data: Dict[str, Any]) -> str:
        """Create a new job, push its id onto the main queue, return the job_id."""
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        job_payload = {
            "job_id": job_id,
            "job_type": job_type,
            "status": JobStatus.IN_PROGRESS.value,
            "data": json.dumps(data),
            "result": "",
            "error": "",
            "start_time": now,
            "end_time": "",
        }
        self.redis.hset(f"{JOB_KEY_PREFIX}{job_id}", mapping=job_payload)
        self.redis.rpush(QUEUE_KEY, job_id)
        logger.info("Job created: id=%s type=%s", job_id, job_type)
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Read the current state of a job."""
        raw = self.redis.hgetall(f"{JOB_KEY_PREFIX}{job_id}")
        if not raw:
            return None
        return {
            "job_id": raw["job_id"],
            "job_type": raw["job_type"],
            "status": raw["status"],
            "data": json.loads(raw["data"]) if raw.get("data") else {},
            "result": json.loads(raw["result"]) if raw.get("result") else None,
            "error": raw.get("error") or None,
            "start_time": raw.get("start_time") or None,
            "end_time": raw.get("end_time") or None,
        }

    def mark_success(self, job_id: str, result: Dict[str, Any]) -> None:
        """Transition job to SUCCESS with result payload."""
        now = datetime.now(timezone.utc).isoformat()
        key = f"{JOB_KEY_PREFIX}{job_id}"
        self.redis.hset(key, mapping={
            "status": JobStatus.SUCCESS.value,
            "result": json.dumps(result),
            "end_time": now,
        })
        self.redis.expire(key, JOB_TTL_SECONDS)
        logger.info("Job completed successfully: id=%s", job_id)

    def mark_failed(self, job_id: str, error_message: str) -> None:
        """Transition job to FAILED with error details."""
        now = datetime.now(timezone.utc).isoformat()
        key = f"{JOB_KEY_PREFIX}{job_id}"
        self.redis.hset(key, mapping={
            "status": JobStatus.FAILED.value,
            "error": error_message,
            "end_time": now,
        })
        self.redis.expire(key, JOB_TTL_SECONDS)
        logger.error("Job failed: id=%s error=%s", job_id, error_message)

    def dequeue(self, timeout: int = 5) -> Optional[str]:
        """Block-pop the next job_id from the main queue (BLPOP)."""
        result = self.redis.blpop(QUEUE_KEY, timeout=timeout)
        if result:
            return result[1]  # (queue_name, job_id)
        return None
