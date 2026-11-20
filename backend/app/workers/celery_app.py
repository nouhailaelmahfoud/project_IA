import os

from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("migration", broker=REDIS_URL, backend=REDIS_URL,
                    include=["backend.app.workers.tasks"])