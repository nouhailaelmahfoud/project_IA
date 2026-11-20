import json
import os

import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
TTL = 7 * 24 * 3600  # un job est gardé 7 jours


def save_job(job: dict) -> None:
    _redis.set(f"job:{job['job_id']}", json.dumps(job, default=str), ex=TTL)


def get_job(job_id: str):
    raw = _redis.get(f"job:{job_id}")
    return json.loads(raw) if raw else None


def update_job(job_id: str, **fields) -> dict:
    job = get_job(job_id)
    job.update(fields)
    save_job(job)
    return job